pub mod infer;
use chrono::DateTime;
mod patterns;
mod strptime;

use chrono::ParseError;
pub use patterns::Pattern;
#[cfg(feature = "dtype-time")]
use polars_core::chunked_array::temporal::time_to_time64ns;

use super::*;
#[cfg(feature = "dtype-date")]
use crate::chunkedarray::date::naive_date_to_date;
use crate::prelude::utf8::strptime::StrpTimeState;

#[cfg(feature = "dtype-time")]
fn time_pattern<F, K>(val: &str, convert: F) -> Option<&'static str>
// (string, fmt) -> PolarsResult
where
    F: Fn(&str, &str) -> chrono::ParseResult<K>,
{
    ["%T", "%T%.3f", "%T%.6f", "%T%.9f"]
        .into_iter()
        .find(|&fmt| convert(val, fmt).is_ok())
}

fn datetime_pattern<F, K>(val: &str, convert: F) -> Option<&'static str>
// (string, fmt) -> PolarsResult
where
    F: Fn(&str, &str) -> chrono::ParseResult<K>,
{
    let result = patterns::DATETIME_Y_M_D
        .iter()
        .find(|fmt| convert(val, fmt).is_ok())
        .copied();
    result.or_else(|| {
        patterns::DATETIME_D_M_Y
            .iter()
            .find(|fmt| convert(val, fmt).is_ok())
            .copied()
    })
}

fn date_pattern<F, K>(val: &str, convert: F) -> Option<&'static str>
// (string, fmt) -> PolarsResult
where
    F: Fn(&str, &str) -> chrono::ParseResult<K>,
{
    let result = patterns::DATE_Y_M_D
        .iter()
        .find(|fmt| convert(val, fmt).is_ok())
        .copied();
    result.or_else(|| {
        patterns::DATE_D_M_Y
            .iter()
            .find(|fmt| convert(val, fmt).is_ok())
            .copied()
    })
}

struct ParseErrorByteCopy(ParseErrorKind);

impl From<ParseError> for ParseErrorByteCopy {
    fn from(e: ParseError) -> Self {
        // we need to do this until chrono ParseErrorKind is public
        // blocked by https://github.com/chronotope/chrono/pull/588
        unsafe { std::mem::transmute(e) }
    }
}

#[allow(dead_code)]
enum ParseErrorKind {
    OutOfRange,
    Impossible,
    NotEnough,
    Invalid,
    /// The input string has been prematurely ended.
    TooShort,
    TooLong,
    BadFormat,
}

fn get_first_val(ca: &Utf8Chunked) -> PolarsResult<&str> {
    let idx = ca.first_non_null().ok_or_else(|| {
        polars_err!(ComputeError:
            "unable to determine date parsing format, all values are null",
        )
    })?;
    Ok(ca.get(idx).expect("should not be null"))
}

#[cfg(feature = "dtype-datetime")]
fn sniff_fmt_datetime(ca_utf8: &Utf8Chunked) -> PolarsResult<&'static str> {
    let val = get_first_val(ca_utf8)?;
    match datetime_pattern(val, NaiveDateTime::parse_from_str) {
        Some(pattern) => Ok(pattern),
        None => match datetime_pattern(val, NaiveDate::parse_from_str) {
            Some(pattern) => Ok(pattern),
            None => polars_bail!(parse_fmt_idk = "datetime"),
        },
    }
}

#[cfg(feature = "dtype-date")]
fn sniff_fmt_date(ca_utf8: &Utf8Chunked) -> PolarsResult<&'static str> {
    let val = get_first_val(ca_utf8)?;
    if let Some(pattern) = date_pattern(val, NaiveDate::parse_from_str) {
        return Ok(pattern);
    }
    polars_bail!(parse_fmt_idk = "date");
}

#[cfg(feature = "dtype-time")]
fn sniff_fmt_time(ca_utf8: &Utf8Chunked) -> PolarsResult<&'static str> {
    let val = get_first_val(ca_utf8)?;
    if let Some(pattern) = time_pattern(val, NaiveTime::parse_from_str) {
        return Ok(pattern);
    }
    polars_bail!(parse_fmt_idk = "time");
}

pub trait Utf8Methods: AsUtf8 {
    #[cfg(feature = "dtype-time")]
    /// Parsing string values and return a [`TimeChunked`]
    fn as_time(&self, fmt: Option<&str>, cache: bool) -> PolarsResult<TimeChunked> {
        let utf8_ca = self.as_utf8();
        let fmt = match fmt {
            Some(fmt) => fmt,
            None => sniff_fmt_time(utf8_ca)?,
        };
        let cache = cache && utf8_ca.len() > 50;

        let mut cache_map = PlHashMap::new();

        let mut ca: Int64Chunked = match utf8_ca.has_validity() {
            false => utf8_ca
                .into_no_null_iter()
                .map(|s| {
                    if cache {
                        *cache_map.entry(s).or_insert_with(|| {
                            NaiveTime::parse_from_str(s, fmt)
                                .ok()
                                .as_ref()
                                .map(time_to_time64ns)
                        })
                    } else {
                        NaiveTime::parse_from_str(s, fmt)
                            .ok()
                            .as_ref()
                            .map(time_to_time64ns)
                    }
                })
                .collect_trusted(),
            _ => utf8_ca
                .into_iter()
                .map(|opt_s| {
                    let opt_nd = opt_s.map(|s| {
                        if cache {
                            *cache_map.entry(s).or_insert_with(|| {
                                NaiveTime::parse_from_str(s, fmt)
                                    .ok()
                                    .as_ref()
                                    .map(time_to_time64ns)
                            })
                        } else {
                            NaiveTime::parse_from_str(s, fmt)
                                .ok()
                                .as_ref()
                                .map(time_to_time64ns)
                        }
                    });
                    match opt_nd {
                        None => None,
                        Some(None) => None,
                        Some(Some(nd)) => Some(nd),
                    }
                })
                .collect_trusted(),
        };
        ca.rename(utf8_ca.name());
        Ok(ca.into())
    }

    #[cfg(feature = "dtype-date")]
    /// Parsing string values and return a [`DateChunked`]
    /// Different from `as_date` this function allows matches that not contain the whole string
    /// e.g. "foo-2021-01-01-bar" could match "2021-01-01"
    fn as_date_not_exact(&self, fmt: Option<&str>) -> PolarsResult<DateChunked> {
        let utf8_ca = self.as_utf8();
        let fmt = match fmt {
            Some(fmt) => fmt,
            None => sniff_fmt_date(utf8_ca)?,
        };
        let mut ca: Int32Chunked = utf8_ca
            .into_iter()
            .map(|opt_s| match opt_s {
                None => None,
                Some(mut s) => {
                    let fmt_len = fmt.len();

                    for i in 1..(s.len().saturating_sub(fmt_len)) {
                        if s.is_empty() {
                            return None;
                        }
                        match NaiveDate::parse_from_str(s, fmt).map(naive_date_to_date) {
                            Ok(nd) => return Some(nd),
                            Err(e) => {
                                let e: ParseErrorByteCopy = e.into();
                                match e.0 {
                                    ParseErrorKind::TooLong => {
                                        s = &s[..s.len() - 1];
                                    },
                                    _ => {
                                        s = &s[i..];
                                    },
                                }
                            },
                        }
                    }
                    None
                },
            })
            .collect_trusted();
        ca.rename(utf8_ca.name());
        Ok(ca.into())
    }

    #[cfg(feature = "dtype-datetime")]
    /// Parsing string values and return a [`DatetimeChunked`]
    /// Different from `as_datetime` this function allows matches that not contain the whole string
    /// e.g. "foo-2021-01-01-bar" could match "2021-01-01"
    fn as_datetime_not_exact(
        &self,
        fmt: Option<&str>,
        tu: TimeUnit,
        tz_aware: bool,
        tz: Option<&TimeZone>,
        _use_earliest: Option<bool>,
    ) -> PolarsResult<DatetimeChunked> {
        let utf8_ca = self.as_utf8();
        let fmt = match fmt {
            Some(fmt) => fmt,
            None => sniff_fmt_datetime(utf8_ca)?,
        };

        let func = match tu {
            TimeUnit::Nanoseconds => datetime_to_timestamp_ns,
            TimeUnit::Microseconds => datetime_to_timestamp_us,
            TimeUnit::Milliseconds => datetime_to_timestamp_ms,
        };

        let mut ca: Int64Chunked = utf8_ca
            .into_iter()
            .map(|opt_s| match opt_s {
                None => None,
                Some(mut s) => {
                    let fmt_len = fmt.len();

                    for i in 1..(s.len().saturating_sub(fmt_len)) {
                        if s.is_empty() {
                            return None;
                        }
                        let timestamp = match tz_aware {
                            true => DateTime::parse_from_str(s, fmt).map(|dt| func(dt.naive_utc())),
                            false => NaiveDateTime::parse_from_str(s, fmt).map(func),
                        };
                        match timestamp {
                            Ok(ts) => return Some(ts),
                            Err(e) => {
                                let e: ParseErrorByteCopy = e.into();
                                match e.0 {
                                    ParseErrorKind::TooLong => {
                                        s = &s[..s.len() - 1];
                                    },
                                    _ => {
                                        s = &s[i..];
                                    },
                                }
                            },
                        }
                    }
                    None
                },
            })
            .collect_trusted();
        ca.rename(utf8_ca.name());
        match (tz_aware, tz) {
            #[cfg(feature = "timezones")]
            (false, Some(tz)) => polars_ops::prelude::replace_time_zone(
                &ca.into_datetime(tu, None),
                Some(tz),
                _use_earliest,
            ),
            #[cfg(feature = "timezones")]
            (true, _) => Ok(ca.into_datetime(tu, Some("UTC".to_string()))),
            _ => Ok(ca.into_datetime(tu, None)),
        }
    }

    #[cfg(feature = "dtype-date")]
    /// Parsing string values and return a [`DateChunked`]
    fn as_date(&self, fmt: Option<&str>, cache: bool) -> PolarsResult<DateChunked> {
        let utf8_ca = self.as_utf8();
        let fmt = match fmt {
            Some(fmt) => fmt,
            None => return infer::to_date(utf8_ca),
        };
        let cache = cache && utf8_ca.len() > 50;
        let fmt = strptime::compile_fmt(fmt)?;
        let mut cache_map = PlHashMap::new();

        // we can use the fast parser
        let mut ca: Int32Chunked = if let Some(fmt_len) = strptime::fmt_len(fmt.as_bytes()) {
            let mut strptime_cache = StrpTimeState::default();
            let mut convert = |s: &str| {
                // Safety:
                // fmt_len is correct, it was computed with this `fmt` str.
                match unsafe { strptime_cache.parse(s.as_bytes(), fmt.as_bytes(), fmt_len) } {
                    // fallback to chrono
                    None => NaiveDate::parse_from_str(s, &fmt).ok(),
                    Some(ndt) => Some(ndt.date()),
                }
                .map(naive_date_to_date)
            };

            if utf8_ca.null_count() == 0 {
                utf8_ca
                    .into_no_null_iter()
                    .map(|val| {
                        if cache {
                            *cache_map.entry(val).or_insert_with(|| convert(val))
                        } else {
                            convert(val)
                        }
                    })
                    .collect_trusted()
            } else {
                utf8_ca
                    .into_iter()
                    .map(|opt_s| {
                        opt_s.and_then(|val| {
                            if cache {
                                *cache_map.entry(val).or_insert_with(|| convert(val))
                            } else {
                                convert(val)
                            }
                        })
                    })
                    .collect_trusted()
            }
        } else {
            utf8_ca
                .into_iter()
                .map(|opt_s| {
                    opt_s.and_then(|s| {
                        if cache {
                            *cache_map.entry(s).or_insert_with(|| {
                                NaiveDate::parse_from_str(s, &fmt)
                                    .ok()
                                    .map(naive_date_to_date)
                            })
                        } else {
                            NaiveDate::parse_from_str(s, &fmt)
                                .ok()
                                .map(naive_date_to_date)
                        }
                    })
                })
                .collect_trusted()
        };

        ca.rename(utf8_ca.name());
        Ok(ca.into())
    }

    #[cfg(feature = "dtype-datetime")]
    /// Parsing string values and return a [`DatetimeChunked`]
    fn as_datetime(
        &self,
        fmt: Option<&str>,
        tu: TimeUnit,
        cache: bool,
        tz_aware: bool,
        tz: Option<&TimeZone>,
        use_earliest: Option<bool>,
    ) -> PolarsResult<DatetimeChunked> {
        let utf8_ca = self.as_utf8();
        let fmt = match fmt {
            Some(fmt) => fmt,
            None => return infer::to_datetime(utf8_ca, tu, tz, use_earliest),
        };
        let fmt = strptime::compile_fmt(fmt)?;
        let cache = cache && utf8_ca.len() > 50;

        let func = match tu {
            TimeUnit::Nanoseconds => datetime_to_timestamp_ns,
            TimeUnit::Microseconds => datetime_to_timestamp_us,
            TimeUnit::Milliseconds => datetime_to_timestamp_ms,
        };

        if tz_aware {
            #[cfg(feature = "timezones")]
            {
                use polars_arrow::export::hashbrown::hash_map::Entry;
                let mut cache_map = PlHashMap::new();

                let convert = |s: &str| {
                    DateTime::parse_from_str(s, &fmt)
                        .ok()
                        .map(|dt| func(dt.naive_utc()))
                };

                let mut ca: Int64Chunked = utf8_ca
                    .into_iter()
                    .map(|opt_s| {
                        opt_s
                            .map(|s| {
                                let out = if cache {
                                    match cache_map.entry(s) {
                                        Entry::Vacant(entry) => {
                                            let value = convert(s);
                                            entry.insert(value);
                                            value
                                        },
                                        Entry::Occupied(val) => *val.get(),
                                    }
                                } else {
                                    convert(s)
                                };
                                Ok(out)
                            })
                            .transpose()
                            .map(|options| options.flatten())
                    })
                    .collect::<PolarsResult<_>>()?;

                ca.rename(utf8_ca.name());
                Ok(ca.into_datetime(tu, Some("UTC".to_string())))
            }
            #[cfg(not(feature = "timezones"))]
            {
                panic!("activate 'timezones' feature")
            }
        } else {
            let mut cache_map = PlHashMap::new();
            let transform = match tu {
                TimeUnit::Nanoseconds => infer::transform_datetime_ns,
                TimeUnit::Microseconds => infer::transform_datetime_us,
                TimeUnit::Milliseconds => infer::transform_datetime_ms,
            };
            // we can use the fast parser
            let mut ca: Int64Chunked = if let Some(fmt_len) =
                self::strptime::fmt_len(fmt.as_bytes())
            {
                let mut strptime_cache = StrpTimeState::default();
                let mut convert = |s: &str| {
                    // Safety:
                    // fmt_len is correct, it was computed with this `fmt` str.
                    match unsafe { strptime_cache.parse(s.as_bytes(), fmt.as_bytes(), fmt_len) } {
                        None => transform(s, &fmt),
                        Some(ndt) => Some(func(ndt)),
                    }
                };
                if utf8_ca.null_count() == 0 {
                    utf8_ca
                        .into_no_null_iter()
                        .map(|val| {
                            if cache {
                                *cache_map.entry(val).or_insert_with(|| convert(val))
                            } else {
                                convert(val)
                            }
                        })
                        .collect_trusted()
                } else {
                    utf8_ca
                        .into_iter()
                        .map(|opt_s| {
                            opt_s.and_then(|val| {
                                if cache {
                                    *cache_map.entry(val).or_insert_with(|| convert(val))
                                } else {
                                    convert(val)
                                }
                            })
                        })
                        .collect_trusted()
                }
            } else {
                let mut cache_map = PlHashMap::new();
                utf8_ca
                    .into_iter()
                    .map(|opt_s| {
                        opt_s.and_then(|s| {
                            if cache {
                                *cache_map.entry(s).or_insert_with(|| transform(s, &fmt))
                            } else {
                                transform(s, &fmt)
                            }
                        })
                    })
                    .collect_trusted()
            };
            ca.rename(utf8_ca.name());
            match tz {
                #[cfg(feature = "timezones")]
                Some(tz) => polars_ops::prelude::replace_time_zone(
                    &ca.into_datetime(tu, None),
                    Some(tz),
                    use_earliest,
                ),
                _ => Ok(ca.into_datetime(tu, None)),
            }
        }
    }
}

pub trait AsUtf8 {
    fn as_utf8(&self) -> &Utf8Chunked;
}

impl AsUtf8 for Utf8Chunked {
    fn as_utf8(&self) -> &Utf8Chunked {
        self
    }
}

impl Utf8Methods for Utf8Chunked {}
