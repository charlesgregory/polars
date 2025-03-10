from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import reduce
from typing import Any, Sequence

import numpy as np
import pytest

import polars as pl
from polars.exceptions import PolarsInefficientApplyWarning
from polars.testing import assert_frame_equal


def test_apply_none() -> None:
    df = pl.DataFrame(
        {
            "g": [1, 1, 1, 2, 2, 2, 5],
            "a": [2, 4, 5, 190, 1, 4, 1],
            "b": [1, 3, 2, 1, 43, 3, 1],
        }
    )

    out = (
        df.group_by("g", maintain_order=True).agg(
            pl.apply(
                exprs=["a", pl.col("b") ** 4, pl.col("a") / 4],
                function=lambda x: x[0] * x[1] + x[2].sum(),
            ).alias("multiple")
        )
    )["multiple"]
    assert out[0].to_list() == [4.75, 326.75, 82.75]
    assert out[1].to_list() == [238.75, 3418849.75, 372.75]

    out_df = df.select(pl.map(exprs=["a", "b"], function=lambda s: s[0] * s[1]))
    assert out_df["a"].to_list() == (df["a"] * df["b"]).to_list()

    # check if we can return None
    def func(s: Sequence[pl.Series]) -> pl.Series | None:
        if s[0][0] == 190:
            return None
        else:
            return s[0]

    out = (
        df.group_by("g", maintain_order=True).agg(
            pl.apply(
                exprs=["a", pl.col("b") ** 4, pl.col("a") / 4], function=func
            ).alias("multiple")
        )
    )["multiple"]
    assert out[1] is None


def test_apply_return_py_object() -> None:
    df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    out = df.select([pl.all().map(lambda s: reduce(lambda a, b: a + b, s))])
    assert out.rows() == [(6, 15)]


def test_agg_objects() -> None:
    df = pl.DataFrame(
        {
            "names": ["foo", "ham", "spam", "cheese", "egg", "foo"],
            "dates": ["1", "1", "2", "3", "3", "4"],
            "groups": ["A", "A", "B", "B", "B", "C"],
        }
    )

    class Foo:
        def __init__(self, payload: Any):
            self.payload = payload

    out = df.group_by("groups").agg(
        [
            pl.apply(
                [pl.col("dates"), pl.col("names")], lambda s: Foo(dict(zip(s[0], s[1])))
            )
        ]
    )
    assert out.dtypes == [pl.Utf8, pl.Object]


def test_apply_infer_list() -> None:
    df = pl.DataFrame(
        {
            "int": [1, 2],
            "str": ["a", "b"],
            "bool": [True, None],
        }
    )
    assert df.select([pl.all().apply(lambda x: [x])]).dtypes == [pl.List] * 3


def test_apply_arithmetic_consistency() -> None:
    df = pl.DataFrame({"A": ["a", "a"], "B": [2, 3]})
    with pytest.warns(
        PolarsInefficientApplyWarning, match="In this case, you can replace"
    ):
        assert df.group_by("A").agg(pl.col("B").apply(lambda x: x + 1.0))[
            "B"
        ].to_list() == [[3.0, 4.0]]


def test_apply_struct() -> None:
    df = pl.DataFrame(
        {"A": ["a", "a"], "B": [2, 3], "C": [True, False], "D": [12.0, None]}
    )
    out = df.with_columns(pl.struct(df.columns).alias("struct")).select(
        [
            pl.col("struct").apply(lambda x: x["A"]).alias("A_field"),
            pl.col("struct").apply(lambda x: x["B"]).alias("B_field"),
            pl.col("struct").apply(lambda x: x["C"]).alias("C_field"),
            pl.col("struct").apply(lambda x: x["D"]).alias("D_field"),
        ]
    )
    expected = pl.DataFrame(
        {
            "A_field": ["a", "a"],
            "B_field": [2, 3],
            "C_field": [True, False],
            "D_field": [12.0, None],
        }
    )

    assert_frame_equal(out, expected)


def test_apply_numpy_out_3057() -> None:
    df = pl.DataFrame(
        {
            "id": [0, 0, 0, 1, 1, 1],
            "t": [2.0, 4.3, 5, 10, 11, 14],
            "y": [0.0, 1, 1.3, 2, 3, 4],
        }
    )
    result = df.group_by("id", maintain_order=True).agg(
        pl.apply(["y", "t"], lambda lst: np.trapz(y=lst[0], x=lst[1])).alias("result")
    )
    expected = pl.DataFrame({"id": [0, 1], "result": [1.955, 13.0]})
    assert_frame_equal(result, expected)


def test_apply_numpy_int_out() -> None:
    df = pl.DataFrame({"col1": [2, 4, 8, 16]})
    result = df.with_columns(
        pl.col("col1").apply(lambda x: np.left_shift(x, 8)).alias("result")
    )
    expected = pl.DataFrame({"col1": [2, 4, 8, 16], "result": [512, 1024, 2048, 4096]})
    assert_frame_equal(result, expected)

    df = pl.DataFrame({"col1": [2, 4, 8, 16], "shift": [1, 1, 2, 2]})
    result = df.select(
        pl.struct(["col1", "shift"])
        .apply(lambda cols: np.left_shift(cols["col1"], cols["shift"]))
        .alias("result")
    )
    expected = pl.DataFrame({"result": [4, 8, 32, 64]})
    assert_frame_equal(result, expected)


def test_datelike_identity() -> None:
    for s in [
        pl.Series([datetime(year=2000, month=1, day=1)]),
        pl.Series([timedelta(hours=2)]),
        pl.Series([date(year=2000, month=1, day=1)]),
    ]:
        assert s.apply(lambda x: x).to_list() == s.to_list()


def test_apply_list_anyvalue_fallback() -> None:
    import json

    with pytest.warns(
        PolarsInefficientApplyWarning,
        match=r'(?s)replace your `apply` with.*pl.col\("text"\).str.json_extract()',
    ):
        df = pl.DataFrame({"text": ['[{"x": 1, "y": 2}, {"x": 3, "y": 4}]']})
        assert df.select(pl.col("text").apply(json.loads)).to_dict(False) == {
            "text": [[{"x": 1, "y": 2}, {"x": 3, "y": 4}]]
        }

        # starts with empty list '[]'
        df = pl.DataFrame(
            {
                "text": [
                    "[]",
                    '[{"x": 1, "y": 2}, {"x": 3, "y": 4}]',
                    '[{"x": 1, "y": 2}]',
                ]
            }
        )
        assert df.select(pl.col("text").apply(json.loads)).to_dict(False) == {
            "text": [[], [{"x": 1, "y": 2}, {"x": 3, "y": 4}], [{"x": 1, "y": 2}]]
        }


def test_apply_all_types() -> None:
    dtypes = [
        pl.UInt8,
        pl.UInt16,
        pl.UInt32,
        pl.UInt64,
        pl.Int8,
        pl.Int16,
        pl.Int32,
        pl.Int64,
    ]
    # test we don't panic
    for dtype in dtypes:
        pl.Series([1, 2, 3, 4, 5], dtype=dtype).apply(lambda x: x)


def test_apply_type_propagation() -> None:
    assert (
        pl.from_dict(
            {
                "a": [1, 2, 3],
                "b": [{"c": 1, "d": 2}, {"c": 2, "d": 3}, {"c": None, "d": None}],
            }
        )
        .group_by("a", maintain_order=True)
        .agg(
            [
                pl.when(pl.col("b").null_count() == 0)
                .then(
                    pl.col("b").apply(
                        lambda s: s[0]["c"],
                        return_dtype=pl.Float64,
                    )
                )
                .otherwise(None)
            ]
        )
    ).to_dict(False) == {"a": [1, 2, 3], "b": [1.0, 2.0, None]}


def test_empty_list_in_apply() -> None:
    df = pl.DataFrame(
        {"a": [[1], [1, 2], [3, 4], [5, 6]], "b": [[3], [1, 2], [1, 2], [4, 5]]}
    )

    assert df.select(
        pl.struct(["a", "b"]).apply(lambda row: list(set(row["a"]) & set(row["b"])))
    ).to_dict(False) == {"a": [[], [1, 2], [], [5]]}


def test_apply_skip_nulls() -> None:
    some_map = {None: "a", 1: "b"}
    s = pl.Series([None, 1])

    assert s.apply(lambda x: some_map[x]).to_list() == [None, "b"]
    assert s.apply(lambda x: some_map[x], skip_nulls=False).to_list() == ["a", "b"]


def test_apply_object_dtypes() -> None:
    with pytest.warns(
        PolarsInefficientApplyWarning,
        match=r"(?s)replace your `apply` with.*lambda x:",
    ):
        assert pl.DataFrame(
            {"a": pl.Series([1, 2, "a", 4, 5], dtype=pl.Object)}
        ).with_columns(
            [
                pl.col("a").apply(lambda x: x * 2, return_dtype=pl.Object),
                pl.col("a")
                .apply(lambda x: isinstance(x, (int, float)), return_dtype=pl.Boolean)
                .alias("is_numeric1"),
                pl.col("a")
                .apply(lambda x: isinstance(x, (int, float)))
                .alias("is_numeric_infer"),
            ]
        ).to_dict(
            False
        ) == {
            "a": [2, 4, "aa", 8, 10],
            "is_numeric1": [True, True, False, True, True],
            "is_numeric_infer": [True, True, False, True, True],
        }


def test_apply_explicit_list_output_type() -> None:
    out = pl.DataFrame({"str": ["a", "b"]}).with_columns(
        [
            pl.col("str").apply(
                lambda _: pl.Series([1, 2, 3]), return_dtype=pl.List(pl.Int64)
            )
        ]
    )

    assert out.dtypes == [pl.List(pl.Int64)]
    assert out.to_dict(False) == {"str": [[1, 2, 3], [1, 2, 3]]}


def test_apply_dict() -> None:
    with pytest.warns(
        PolarsInefficientApplyWarning,
        match=r'(?s)replace your `apply` with.*pl.col\("abc"\).str.json_extract()',
    ):
        df = pl.DataFrame({"abc": ['{"A":"Value1"}', '{"B":"Value2"}']})
        assert df.select(pl.col("abc").apply(json.loads)).to_dict(False) == {
            "abc": [{"A": "Value1", "B": None}, {"A": None, "B": "Value2"}]
        }
        assert pl.DataFrame(
            {"abc": ['{"A":"Value1", "B":"Value2"}', '{"B":"Value3"}']}
        ).select(pl.col("abc").apply(json.loads)).to_dict(False) == {
            "abc": [{"A": "Value1", "B": "Value2"}, {"A": None, "B": "Value3"}]
        }


def test_apply_pass_name() -> None:
    df = pl.DataFrame(
        {
            "bar": [1, 1, 2],
            "foo": [1, 2, 3],
        }
    )

    mapper = {"foo": "foo1"}

    def applyer(s: pl.Series) -> pl.Series:
        return pl.Series([mapper[s.name]])

    assert df.group_by("bar", maintain_order=True).agg(
        [
            pl.col("foo").apply(applyer, pass_name=True),
        ]
    ).to_dict(False) == {"bar": [1, 2], "foo": [["foo1"], ["foo1"]]}


def test_apply_binary() -> None:
    assert pl.DataFrame({"bin": [b"\x11" * 12, b"\x22" * 12, b"\xaa" * 12]}).select(
        pl.col("bin").apply(bytes.hex)
    ).to_dict(False) == {
        "bin": [
            "111111111111111111111111",
            "222222222222222222222222",
            "aaaaaaaaaaaaaaaaaaaaaaaa",
        ]
    }


def test_apply_no_dtype_set_8531() -> None:
    assert (
        pl.DataFrame({"a": [1]})
        .with_columns(
            pl.col("a").map(lambda x: x * 2).shift_and_fill(fill_value=0, periods=0)
        )
        .item()
        == 2
    )


def test_apply_set_datetime_output_8984() -> None:
    df = pl.DataFrame({"a": [""]})
    payload = datetime(2001, 1, 1)
    assert df.select(
        pl.col("a").apply(lambda _: payload, return_dtype=pl.Datetime),
    )[
        "a"
    ].to_list() == [payload]


def test_err_df_apply_return_type() -> None:
    df = pl.DataFrame({"a": [[1, 2], [2, 3]], "b": [[4, 5], [6, 7]]})

    def cmb(row: tuple[Any, ...]) -> list[Any]:
        res = [x + y for x, y in zip(row[0], row[1])]
        return [res]

    with pytest.raises(pl.ComputeError, match="expected tuple, got list"):
        df.apply(cmb)


def test_apply_shifted_chunks() -> None:
    df = pl.DataFrame(pl.Series("texts", ["test", "test123", "tests"]))
    assert df.select(
        pl.col("texts"), pl.col("texts").shift(1).alias("texts_shifted")
    ).apply(lambda x: x).to_dict(False) == {
        "column_0": ["test", "test123", "tests"],
        "column_1": [None, "test", "test123"],
    }


def test_apply_dict_order_10128() -> None:
    df = pl.select(pl.lit("").apply(lambda x: {"c": 1, "b": 2, "a": 3}))
    assert df.to_dict(False) == {"literal": [{"c": 1, "b": 2, "a": 3}]}


def test_apply_10237() -> None:
    df = pl.DataFrame({"a": [1, 2, 3]})
    assert df.select(pl.all().apply(lambda x: x > 50))["a"].to_list() == [False] * 3


def test_apply_on_empty_col_10639() -> None:
    df = pl.DataFrame({"A": [], "B": []})
    res = df.group_by("B").agg(
        pl.col("A")
        .apply(lambda x: x, return_dtype=pl.Int32, strategy="threading")
        .alias("Foo")
    )
    assert res.to_dict(False) == {
        "B": [],
        "Foo": [],
    }
    res = df.group_by("B").agg(
        pl.col("A")
        .apply(lambda x: x, return_dtype=pl.Int32, strategy="thread_local")
        .alias("Foo")
    )
    assert res.to_dict(False) == {
        "B": [],
        "Foo": [],
    }
