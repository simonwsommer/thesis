#!/usr/bin/env python3
"""
"""
from typing import Dict
import warnings

import numpy as np
import pandas as pd


def calculate_order_stats(
    order_stats: pd.DataFrame,
    trading_actions: pd.DataFrame,
    metainfo: pd.Series,
    tick_sizes: pd.DataFrame,
    start_microsecond: int,
    end_microsecond: int,
) -> Dict[str, float]:
    if order_stats.empty:
        return empty_result()
    order_stats.set_index("entry_time", inplace=True)
    order_stats.sort_index(inplace=True)
    # filter for start/end
    order_stats = order_stats.loc[start_microsecond:end_microsecond]
    # remove market orders
    order_stats = order_stats.loc[order_stats["price"] != 2147483647]

    # filter based on trading_actions
    if not trading_actions.empty:
        for _, event in trading_actions.iterrows():
            order_stats = order_stats.loc[
                (order_stats.index < event.timestamp)
                | (order_stats.index > event.until)
            ]
    if order_stats.empty:
        return empty_result()

    # filter if filled/removed at the same microsecond as entered
    same_microsecond = order_stats.index == order_stats["first_fill_time"]
    order_stats = order_stats.loc[~same_microsecond]
    same_microsecond = order_stats.index == order_stats["remove_time"]
    order_stats = order_stats.loc[~same_microsecond]

    # time to fill in milliseconds
    order_stats["time_to_fill"] = (
        order_stats["first_fill_time"] - order_stats.index
    ) / 1000

    # time to removal in milliseconds
    order_stats["time_to_removal"] = (
        order_stats["remove_time"] - order_stats.index
    ) / 1000

    # distance to best price, also in number of ticks
    order_stats["distance_to_best"] = abs(
        order_stats["price"] - order_stats["best_price"]
    )
    # unequal join
    conditions = [
        (order_stats.price.values >= step.price_start)
        & (order_stats.price.values < step.price_end)
        for step in tick_sizes[["price_start", "price_end"]].itertuples()
    ]
    order_stats["tick_size"] = np.piecewise(
        np.zeros(order_stats.shape[0]), conditions, tick_sizes.tick_size.values
    )
    order_stats["distance_in_ticks"] = round(
        order_stats["distance_to_best"] / order_stats["tick_size"], 2
    )
    order_stats[["price", "best_price", "distance_to_best", "tick_size"]] /= (
        10 ** metainfo.price_decimals
    )

    stats = dict()

    stats["num_orders_total"] = order_stats.shape[0]
    counts = order_stats["first_fill_time"].isna().value_counts()
    for nan_indicator in counts.index:
        num_orders = counts[nan_indicator]
        if nan_indicator is True:
            stats["num_orders_deleted"] = num_orders
        else:
            stats["num_orders_filled"] = num_orders

    # only look at orders that have been entered at most 1 tick away from best
    columns = [
        "price",
        "quantity_entered",
        "quantity_filled",
        "distance_in_ticks",
        "time_to_fill",
        "time_to_removal",
    ]
    close_to_best = order_stats.loc[order_stats.distance_in_ticks <= 1, columns]

    close_to_best["value_entered"] = (
        close_to_best["price"] * close_to_best["quantity_entered"]
    )
    close_to_best["value_filled"] = (
        close_to_best["price"] * close_to_best["quantity_filled"]
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        stats["time_to_fill_mean"] = close_to_best["time_to_fill"].mean()
        stats["time_to_fill_median"] = close_to_best["time_to_fill"].median()
        stats["time_to_removal_mean"] = close_to_best["time_to_removal"].mean()
        stats["time_to_removal_median"] = close_to_best["time_to_removal"].median()

        stats["value_entered_mean"] = close_to_best["value_entered"].mean()
        stats["value_entered_median"] = close_to_best["value_entered"].median()
        stats["value_entered_total"] = close_to_best["value_entered"].sum()
        stats["value_filled_total"] = close_to_best["value_filled"].sum()

        stats["fill_ratio_mean"] = (
            close_to_best["value_filled"] / close_to_best["value_entered"]
        ).mean()
        stats["fill_ratio_median"] = (
            close_to_best["value_filled"] / close_to_best["value_entered"]
        ).median()
        if stats["value_entered_total"] > 0:
            stats["fill_ratio_total"] = (
                stats["value_filled_total"] / stats["value_entered_total"]
            )
        else:
            stats["fill_ratio_total"] = 0

    return stats


def empty_result():
    return dict()
