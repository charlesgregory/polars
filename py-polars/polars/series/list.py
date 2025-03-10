from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Sequence

from polars import functions as F
from polars.series.utils import expr_dispatch
from polars.utils._wrap import wrap_s
from polars.utils.deprecation import deprecate_renamed_function

if TYPE_CHECKING:
    from datetime import date, datetime, time

    from polars import Expr, Series
    from polars.polars import PySeries
    from polars.type_aliases import NullBehavior, ToStructStrategy


@expr_dispatch
class ListNameSpace:
    """Namespace for list related methods."""

    _accessor = "list"

    def __init__(self, series: Series):
        self._s: PySeries = series._s

    def all(self) -> Expr:
        """
        Evaluate whether all boolean values in a list are true.

        Examples
        --------
        >>> df = pl.DataFrame(
        ...     {"a": [[True, True], [False, True], [False, False], [None], [], None]}
        ... )
        >>> df.select(pl.col("a").list.all())
        shape: (6, 1)
        ┌───────┐
        │ a     │
        │ ---   │
        │ bool  │
        ╞═══════╡
        │ true  │
        │ false │
        │ false │
        │ true  │
        │ true  │
        │ null  │
        └───────┘

        """

    def any(self) -> Expr:
        """
        Evaluate whether any boolean value in a list is true.

        Examples
        --------
        >>> df = pl.DataFrame(
        ...     {"a": [[True, True], [False, True], [False, False], [None], [], None]}
        ... )
        >>> df.select(pl.col("a").list.any())
        shape: (6, 1)
        ┌───────┐
        │ a     │
        │ ---   │
        │ bool  │
        ╞═══════╡
        │ true  │
        │ true  │
        │ false │
        │ false │
        │ false │
        │ null  │
        └───────┘

        """

    def lengths(self) -> Series:
        """
        Get the length of the arrays as UInt32.

        Examples
        --------
        >>> s = pl.Series([[1, 2, 3], [5]])
        >>> s.list.lengths()
        shape: (2,)
        Series: '' [u32]
        [
            3
            1
        ]

        """

    def sum(self) -> Series:
        """Sum all the arrays in the list."""

    def max(self) -> Series:
        """Compute the max value of the arrays in the list."""

    def min(self) -> Series:
        """Compute the min value of the arrays in the list."""

    def mean(self) -> Series:
        """Compute the mean value of the arrays in the list."""

    def sort(self, *, descending: bool = False) -> Series:
        """
        Sort the arrays in this column.

        Parameters
        ----------
        descending
            Sort in descending order.

        Examples
        --------
        >>> s = pl.Series("a", [[3, 2, 1], [9, 1, 2]])
        >>> s.list.sort()
        shape: (2,)
        Series: 'a' [list[i64]]
        [
                [1, 2, 3]
                [1, 2, 9]
        ]
        >>> s.list.sort(descending=True)
        shape: (2,)
        Series: 'a' [list[i64]]
        [
                [3, 2, 1]
                [9, 2, 1]
        ]

        """

    def reverse(self) -> Series:
        """Reverse the arrays in the list."""

    def unique(self, *, maintain_order: bool = False) -> Series:
        """
        Get the unique/distinct values in the list.

        Parameters
        ----------
        maintain_order
            Maintain order of data. This requires more work.

        """

    def concat(self, other: list[Series] | Series | list[Any]) -> Series:
        """
        Concat the arrays in a Series dtype List in linear time.

        Parameters
        ----------
        other
            Columns to concat into a List Series

        """

    def get(self, index: int | Series | list[int]) -> Series:
        """
        Get the value by index in the sublists.

        So index `0` would return the first item of every sublist
        and index `-1` would return the last item of every sublist
        if an index is out of bounds, it will return a `None`.

        Parameters
        ----------
        index
            Index to return per sublist

        """

    def take(
        self, index: Series | list[int] | list[list[int]], *, null_on_oob: bool = False
    ) -> Series:
        """
        Take sublists by multiple indices.

        The indices may be defined in a single column, or by sublists in another
        column of dtype ``List``.

        Parameters
        ----------
        index
            Indices to return per sublist
        null_on_oob
            Behavior if an index is out of bounds:
            True -> set as null
            False -> raise an error
            Note that defaulting to raising an error is much cheaper

        """

    def __getitem__(self, item: int) -> Series:
        return self.get(item)

    def join(self, separator: str) -> Series:
        """
        Join all string items in a sublist and place a separator between them.

        This errors if inner type of list `!= Utf8`.

        Parameters
        ----------
        separator
            string to separate the items with

        Returns
        -------
        Series
            Series of data type :class:`Utf8`.

        Examples
        --------
        >>> s = pl.Series([["foo", "bar"], ["hello", "world"]])
        >>> s.list.join(separator="-")
        shape: (2,)
        Series: '' [str]
        [
            "foo-bar"
            "hello-world"
        ]

        """

    def first(self) -> Series:
        """Get the first value of the sublists."""

    def last(self) -> Series:
        """Get the last value of the sublists."""

    def contains(self, item: float | str | bool | int | date | datetime) -> Series:
        """
        Check if sublists contain the given item.

        Parameters
        ----------
        item
            Item that will be checked for membership

        Returns
        -------
        Series
            Series of data type :class:`Boolean`.

        """

    def arg_min(self) -> Series:
        """
        Retrieve the index of the minimal value in every sublist.

        Returns
        -------
        Series
            Series of data type :class:`UInt32` or :class:`UInt64`
            (depending on compilation).

        """

    def arg_max(self) -> Series:
        """
        Retrieve the index of the maximum value in every sublist.

        Returns
        -------
        Series
            Series of data type :class:`UInt32` or :class:`UInt64`
            (depending on compilation).

        """

    def diff(self, n: int = 1, null_behavior: NullBehavior = "ignore") -> Series:
        """
        Calculate the n-th discrete difference of every sublist.

        Parameters
        ----------
        n
            Number of slots to shift.
        null_behavior : {'ignore', 'drop'}
            How to handle null values.

        Examples
        --------
        >>> s = pl.Series("a", [[1, 2, 3, 4], [10, 2, 1]])
        >>> s.list.diff()
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [null, 1, … 1]
            [null, -8, -1]
        ]

        >>> s.list.diff(n=2)
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [null, null, … 2]
            [null, null, -9]
        ]

        >>> s.list.diff(n=2, null_behavior="drop")
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [2, 2]
            [-9]
        ]

        """

    def shift(self, periods: int = 1) -> Series:
        """
        Shift values by the given period.

        Parameters
        ----------
        periods
            Number of places to shift (may be negative).

        Examples
        --------
        >>> s = pl.Series("a", [[1, 2, 3, 4], [10, 2, 1]])
        >>> s.list.shift()
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [null, 1, … 3]
            [null, 10, 2]
        ]

        """

    def slice(self, offset: int | Expr, length: int | Expr | None = None) -> Series:
        """
        Slice every sublist.

        Parameters
        ----------
        offset
            Start index. Negative indexing is supported.
        length
            Length of the slice. If set to ``None`` (default), the slice is taken to the
            end of the list.

        Examples
        --------
        >>> s = pl.Series("a", [[1, 2, 3, 4], [10, 2, 1]])
        >>> s.list.slice(1, 2)
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [2, 3]
            [2, 1]
        ]

        """

    def head(self, n: int | Expr = 5) -> Series:
        """
        Slice the first `n` values of every sublist.

        Parameters
        ----------
        n
            Number of values to return for each sublist.

        Examples
        --------
        >>> s = pl.Series("a", [[1, 2, 3, 4], [10, 2, 1]])
        >>> s.list.head(2)
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [1, 2]
            [10, 2]
        ]

        """

    def tail(self, n: int | Expr = 5) -> Series:
        """
        Slice the last `n` values of every sublist.

        Parameters
        ----------
        n
            Number of values to return for each sublist.

        Examples
        --------
        >>> s = pl.Series("a", [[1, 2, 3, 4], [10, 2, 1]])
        >>> s.list.tail(2)
        shape: (2,)
        Series: 'a' [list[i64]]
        [
            [3, 4]
            [2, 1]
        ]

        """

    def explode(self) -> Series:
        """
        Returns a column with a separate row for every list element.

        Returns
        -------
        Series
            Series with the data type of the list elements.

        See Also
        --------
        Series.reshape : Reshape this Series to a flat Series or a Series of Lists.

        Examples
        --------
        >>> s = pl.Series("a", [[1, 2, 3], [4, 5, 6]])
        >>> s.list.explode()
        shape: (6,)
        Series: 'a' [i64]
        [
            1
            2
            3
            4
            5
            6
        ]

        """

    def count_match(
        self, element: float | str | bool | int | date | datetime | time | Expr
    ) -> Expr:
        """
        Count how often the value produced by ``element`` occurs.

        Parameters
        ----------
        element
            An expression that produces a single value

        """

    def to_struct(
        self,
        n_field_strategy: ToStructStrategy = "first_non_null",
        fields: Callable[[int], str] | Sequence[str] | None = None,
    ) -> Series:
        """
        Convert the series of type ``List`` to a series of type ``Struct``.

        Parameters
        ----------
        n_field_strategy : {'first_non_null', 'max_width'}
            Strategy to determine the number of fields of the struct.

            * "first_non_null": set number of fields equal to the length of the
              first non zero-length sublist.
            * "max_width": set number of fields as max length of all sublists.
        fields
            If the name and number of the desired fields is known in advance
            a list of field names can be given, which will be assigned by index.
            Otherwise, to dynamically assign field names, a custom function can be
            used; if neither are set, fields will be `field_0, field_1 .. field_n`.

        Examples
        --------
        Convert list to struct with default field name assignment:

        >>> s1 = pl.Series("n", [[0, 1, 2], [0, 1]])
        >>> s2 = s1.list.to_struct()
        >>> s2
        shape: (2,)
        Series: 'n' [struct[3]]
        [
            {0,1,2}
            {0,1,null}
        ]
        >>> s2.struct.fields
        ['field_0', 'field_1', 'field_2']

        Convert list to struct with field name assignment by function/index:

        >>> s3 = s1.list.to_struct(fields=lambda idx: f"n{idx:02}")
        >>> s3.struct.fields
        ['n00', 'n01', 'n02']

        Convert list to struct with field name assignment by index from a list of names:

        >>> s1.list.to_struct(fields=["one", "two", "three"]).struct.unnest()
        shape: (2, 3)
        ┌─────┬─────┬───────┐
        │ one ┆ two ┆ three │
        │ --- ┆ --- ┆ ---   │
        │ i64 ┆ i64 ┆ i64   │
        ╞═════╪═════╪═══════╡
        │ 0   ┆ 1   ┆ 2     │
        │ 0   ┆ 1   ┆ null  │
        └─────┴─────┴───────┘

        """
        s = wrap_s(self._s)
        return (
            s.to_frame()
            .select(
                F.col(s.name).list.to_struct(
                    # note: in eager mode, 'upper_bound' is always zero, as (unlike
                    # in lazy mode) there is no need to determine/track the schema.
                    n_field_strategy,
                    fields,
                    upper_bound=0,
                )
            )
            .to_series()
        )

    def eval(self, expr: Expr, *, parallel: bool = False) -> Series:
        """
        Run any polars expression against the lists' elements.

        Parameters
        ----------
        expr
            Expression to run. Note that you can select an element with `pl.first()`, or
            `pl.col()`
        parallel
            Run all expression parallel. Don't activate this blindly.
            Parallelism is worth it if there is enough work to do per thread.

            This likely should not be use in the group by context, because we already
            parallel execution per group

        Examples
        --------
        >>> df = pl.DataFrame({"a": [1, 8, 3], "b": [4, 5, 2]})
        >>> df.with_columns(
        ...     pl.concat_list(["a", "b"]).list.eval(pl.element().rank()).alias("rank")
        ... )
        shape: (3, 3)
        ┌─────┬─────┬────────────┐
        │ a   ┆ b   ┆ rank       │
        │ --- ┆ --- ┆ ---        │
        │ i64 ┆ i64 ┆ list[f32]  │
        ╞═════╪═════╪════════════╡
        │ 1   ┆ 4   ┆ [1.0, 2.0] │
        │ 8   ┆ 5   ┆ [2.0, 1.0] │
        │ 3   ┆ 2   ┆ [2.0, 1.0] │
        └─────┴─────┴────────────┘

        """

    def set_union(self, other: Series) -> Series:
        """
        Compute the SET UNION between the elements in this list and the elements of ``other``.

        Parameters
        ----------
        other
            Right hand side of the set operation.

        Examples
        --------
        >>> a = pl.Series([[1, 2, 3], [], [None, 3], [5, 6, 7]])
        >>> b = pl.Series([[2, 3, 4], [3], [3, 4, None], [6, 8]])
        >>> a.list.set_union(b)  # doctest: +IGNORE_RESULT
        shape: (4,)
        Series: '' [list[i64]]
        [
                [1, 2, 3, 4]
                [3]
                [null, 3, 4]
                [5, 6, 7, 8]
        ]

        """  # noqa: W505

    def set_difference(self, other: Series) -> Series:
        """
        Compute the SET DIFFERENCE between the elements in this list and the elements of ``other``.

        Parameters
        ----------
        other
            Right hand side of the set operation.

        See Also
        --------
        polars.Series.list.diff: Calculates the n-th discrete difference of every sublist.

        Examples
        --------
        >>> a = pl.Series([[1, 2, 3], [], [None, 3], [5, 6, 7]])
        >>> b = pl.Series([[2, 3, 4], [3], [3, 4, None], [6, 8]])
        >>> a.list.set_difference(b)
        shape: (4,)
        Series: '' [list[i64]]
        [
                [1]
                []
                []
                [5, 7]
        ]

        """  # noqa: W505

    def set_intersection(self, other: Series) -> Series:
        """
        Compute the SET INTERSECTION between the elements in this list and the elements of ``other``.

        Parameters
        ----------
        other
            Right hand side of the set operation.

        Examples
        --------
        >>> a = pl.Series([[1, 2, 3], [], [None, 3], [5, 6, 7]])
        >>> b = pl.Series([[2, 3, 4], [3], [3, 4, None], [6, 8]])
        >>> a.list.set_intersection(b)
        shape: (4,)
        Series: '' [list[i64]]
        [
                [2, 3]
                []
                [null, 3]
                [6]
        ]

        """  # noqa: W505

    def set_symmetric_difference(self, other: Series) -> Series:
        """
        Compute the SET SYMMETRIC DIFFERENCE between the elements in this list and the elements of ``other``.

        Parameters
        ----------
        other
            Right hand side of the set operation.

        """  # noqa: W505

    @deprecate_renamed_function("set_union", version="0.18.10")
    def union(self, other: Series) -> Series:
        """
        Compute the SET UNION between the elements in this list and the elements of ``other``.

        .. deprecated:: 0.18.10
            This method has been renamed to ``Series.list.set_union``.

        """  # noqa: W505
        return self.set_union(other)

    @deprecate_renamed_function("set_difference", version="0.18.10")
    def difference(self, other: Series) -> Series:
        """
        Compute the SET DIFFERENCE between the elements in this list and the elements of ``other``.

        .. deprecated:: 0.18.10
            This method has been renamed to ``Series.list.set_difference``.

        """  # noqa: W505
        return self.set_difference(other)

    @deprecate_renamed_function("set_intersection", version="0.18.10")
    def intersection(self, other: Series) -> Series:
        """
        Compute the SET INTERSECTION between the elements in this list and the elements of ``other``.

        .. deprecated:: 0.18.10
            This method has been renamed to ``Series.list.set_intersection``.

        """  # noqa: W505
        return self.set_intersection(other)

    @deprecate_renamed_function("set_symmetric_difference", version="0.18.10")
    def symmetric_difference(self, other: Series) -> Series:
        """
        Compute the SET SYMMETRIC DIFFERENCE between the elements in this list and the elements of ``other``.

        .. deprecated:: 0.18.10
            This method has been renamed to ``Series.list.set_symmetric_difference``.

        """  # noqa: W505
        return self.set_symmetric_difference(other)
