#!/usr/bin/env python3
"""
"""

# standard libraries
import cProfile, pstats
from multiprocessing import Pool
import os
from pathlib import Path
import pickle
import sys
import time
from typing import Dict, List, Iterator

# third-party packages
import pandas as pd
from tqdm import tqdm

from process_messages.orderbook_stats import SingleDayIMIData
from calculate_statistics.calculate import calculate_orderbook_stats


def main():

    data_path = Path.home() / "data/ITCH_market_data/binary"
    binary_file_paths = data_path.glob("*.bin")

    start_time = time.time()
    num_files = len(list(data_path.glob("*.bin")))

    print(f"Processing {num_files} dates (1 file per date)")
    results = load_and_process_all(binary_file_paths)
    print(f"It took {round(time.time() - start_time, 2)} seconds to process {num_files} dates")

    timestamp = str(pd.Timestamp("today"))
    os.makedirs("results", exist_ok=True)
    with open(f"results/results_{timestamp}.pickle", "wb") as pickle_file:
        pickle.dump(results, pickle_file)


def load_and_process_all(file_paths: Iterator[Path]) -> List[tuple]:
    with Pool(processes=os.cpu_count() - 1) as pool:
        results = list(tqdm(pool.imap_unordered(load_and_process_orderbook_stats, file_paths)))
    return results


def load_and_process_orderbook_stats(file_path: Path):
    this_day_imi_data = SingleDayIMIData(file_path)
    this_day_imi_data.process_messages()
    results = calculate_orderbook_stats(this_day_imi_data)
    return results


if __name__ == "__main__":
    main()
