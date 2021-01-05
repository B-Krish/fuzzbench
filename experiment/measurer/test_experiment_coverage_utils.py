# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions andsss
# limitations under the License.
"""Tests for experiment_coverage_utils.py"""
import os
import pandas as pd
import multiprocessing

from experiment.measurer import experiment_coverage_utils
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')

# Expected Constants.
SUMMARY_JSON_FILES = ['cov_summary.json', 'cov_summary_1.json',
                      'cov_summary_2.json', 'cov_summary_3.json',
                      'cov_summary_4.json']
NUM_FUNCTION_IN_COV_SUMMARY = 3
NUM_COVERED_SEGMENTS_IN_COV_SUMMARY = 16
FILE_NAME = "/home/test/fuzz_no_fuzzer.cc"
FUNCTION_NAMES = ['main', '_Z3fooIfEvT_', '_Z3fooIiEvT_']
BENCHMARKS = ['benchmark_1', 'benchmark_2']
FUZZERS = ['fuzzer_1', 'fuzzer_2']
TIMESTAMPS = [900, 1800]
TRIAL_IDS = [1, 2, 3, 4, 5]


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


def test_data_frame_container_remove_redundant_duplicates(fs):
    """Tests that remove_redundant_duplicates removes all duplicates entries in
    name_df and segment_df."""

    summary_json_file = get_test_data_path(SUMMARY_JSON_FILES[0])
    fs.add_real_file(summary_json_file, read_only=False)

    df_container = (experiment_coverage_utils.
                    extract_segments_and_functions_from_summary_json(
                        summary_json_file, BENCHMARKS[0], FUZZERS[0],
                        TRIAL_IDS[0], TIMESTAMPS[0]))

    # Drop duplicates using remove_redundant_duplicates().
    df_container.remove_redundant_duplicates()

    # length of data frame after calling remove_redundant_duplicates().
    df_length = len(df_container.segment_df)

    # Force dropping of duplicates again.
    df_after_drop = df_container.segment_df.drop_duplicates(
        subset=df_container.segment_df.columns.difference(['time']))

    # Data frame length after for drop.
    df_length_after_drop = len(df_after_drop)

    # assert length didn't change.
    assert (df_length - df_length_after_drop) == 0


def test_data_frame_utilities_for_function_df(fs):
    """Tests that name_to_id ."""
    json_files = []
    for json_file in SUMMARY_JSON_FILES:
        summary_json_file = get_test_data_path(json_file)
        json_files.append(summary_json_file)
        fs.add_real_file(summary_json_file, read_only=False)

    experiment_specific_df_container = (
        mock_multiprocessing_for_recoding_coverage_data(json_files))

    fuzzer_ids = experiment_specific_df_container.function_df[
        'fuzzer'].unique()
    benchmark_ids = experiment_specific_df_container.function_df[
        'benchmark'].unique()
    function_ids = experiment_specific_df_container.function_df[
        'function'].unique()

    assert len(experiment_specific_df_container.function_df
               ) == NUM_FUNCTION_IN_COV_SUMMARY * 8

    assert_integrity_for_fuzzer_ids(experiment_specific_df_container,
                                    fuzzer_ids)

    assert_integrity_for_benchmark_ids(experiment_specific_df_container,
                                       benchmark_ids)

    for function_id in function_ids:
        # check all function names in the data frames are already known.
        assert (set(
            experiment_specific_df_container.name_df[
                experiment_specific_df_container.name_df[
                    'id'] == function_id]['name'].unique())
                .issubset(FUNCTION_NAMES))
        # Check if function ids match in "function" data frame and "name" data
        # frame.
        assert (experiment_specific_df_container.name_df[
                    experiment_specific_df_container.name_df[
                        'id'] == function_id]
                ['type'].item() == "function")


def test_data_frame_utilities_for_segment_df(fs):
    """Tests that extract_covered_regions_from_summary_json returns the covered
    segments and functions from summary json file."""

    json_files = []
    for json_file in SUMMARY_JSON_FILES:
        summary_json_file = get_test_data_path(json_file)
        json_files.append(summary_json_file)
        fs.add_real_file(summary_json_file, read_only=False)

    experiment_specific_df_container = (
        mock_multiprocessing_for_recoding_coverage_data(json_files))

    fuzzer_ids = experiment_specific_df_container.segment_df['fuzzer'].unique()
    benchmark_ids = experiment_specific_df_container.segment_df[
        'benchmark'].unique()
    file_ids = experiment_specific_df_container.segment_df['file'].unique()

    assert len(experiment_specific_df_container.segment_df
               ) == NUM_COVERED_SEGMENTS_IN_COV_SUMMARY * 4

    assert_integrity_for_fuzzer_ids(experiment_specific_df_container,
                                    fuzzer_ids)

    assert_integrity_for_benchmark_ids(experiment_specific_df_container,
                                       benchmark_ids)

    for file_id in file_ids:
        # check all file names in the dat frame are already known.
        assert (experiment_specific_df_container.name_df[
                    experiment_specific_df_container.name_df[
                        'id'] == file_id]['type'].item() == "file")
        # Check if file ids exactly match in "segment" data frame and "name"
        # data frame.
        assert (file_id == experiment_specific_df_container.name_df[
            experiment_specific_df_container.name_df['name'] == FILE_NAME][
            'id'].item())


def mock_multiprocessing_for_recoding_coverage_data(json_files):

    # Function to call using multiprocessing.
    def mock_record_segment_and_function_coverage(process_specific_containers,
                                                  json_file, benchmark, fuzzer,
                                                  trial_num, time_stamp):
        process_specific_containers.append(
            experiment_coverage_utils.
            extract_segments_and_functions_from_summary_json(
                json_file, benchmark, fuzzer, trial_num, time_stamp))

    # Init experiment specific df container.
    experiment_specific_df_container = (
        experiment_coverage_utils.DataFrameContainer())

    # Set start method for multiprocessing.
    multiprocessing.set_start_method('spawn', force=True)

    with multiprocessing.Pool() as pool, multiprocessing.Manager() as manager:
        process_specific_df_containers = (
            manager.list(  # pytype: disable=attribute-error
                [experiment_specific_df_container]))

        # Args for mock_record_segment_and_function_coverage.
        mock_record_segment_and_function_coverage_args = [
            (process_specific_df_containers, json_file, BENCHMARKS[0],
             FUZZERS[0], trial_id, TIMESTAMPS[0])
            for trial_id, json_file in zip(TRIAL_IDS, json_files)
        ]

        # Start async processes.
        result = pool.starmap_async(
            mock_record_segment_and_function_coverage,
            mock_record_segment_and_function_coverage_args)

    # Collect and remove duplicates.
    if result.ready():
        experiment_specific_df_container.segment_df = pd.concat(
            [df.segment_df for df in process_specific_df_containers],
            ignore_index=True)
        experiment_specific_df_container.function_df = pd.concat(
            [df.function_df for df in process_specific_df_containers],
            ignore_index=True)
        experiment_specific_df_container.name_df = pd.concat(
            [df.name_df for df in process_specific_df_containers],
            ignore_index=True)
        experiment_specific_df_container.remove_redundant_duplicates()
    return experiment_specific_df_container


def assert_integrity_for_fuzzer_ids(experiment_specific_df_container,
                                    fuzzer_ids):
    for fuzzer_id in fuzzer_ids:
        # Check if type recorded for the ID id is "fuzzer".
        assert (experiment_specific_df_container.name_df[
                    experiment_specific_df_container.name_df[
                        'id'] == fuzzer_id]['type'].item() == "fuzzer")
        # Check if fuzzer ids match in "segment" data frame and "name" data
        # frame.
        assert fuzzer_id == experiment_specific_df_container.name_df[
            experiment_specific_df_container.name_df['name'] == 'fuzzer_1'][
            'id'].unique().item()


def assert_integrity_for_benchmark_ids(experiment_specific_df_container,
                                       benchmark_ids):
    for benchmark_id in benchmark_ids:
        # Check if type recorded for the ID id is "benchmark".
        assert (experiment_specific_df_container.name_df[
                    experiment_specific_df_container.name_df[
                        'id'] == benchmark_id]['type'].item() == "benchmark")
        # Check if benchmark ids match in "segment" data frame and "name" data
        # frame.
        assert benchmark_id == experiment_specific_df_container.name_df[
            experiment_specific_df_container.name_df['name'] == 'benchmark_1'][
            'id'].unique().item()
