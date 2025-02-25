"""Copyright 2023 SambaNova Systems, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import os
from subprocess import PIPE, run  # nosec

from transformers import GPT2Tokenizer

from .arg_configs import PackingConfig
from .constants import BoundaryType

GPT2_KEY = "gpt2"
TOKENIZER_CLASSES = {GPT2_KEY: GPT2Tokenizer}
try:
    SEP_STR = "-" * os.get_terminal_size().columns
except OSError:
    SEP_STR = "----------------------------------------------------------------------------------"


def data_prep_arg_builder(parser: argparse.ArgumentParser):
    """Adds all the arguments that are required for data_prep.py's argparser, besides the output_path.

    Args:
        parser (argparse.ArgumentParser): parser to add arguments to
    """
    parser.add_argument("--input_file_path", type=str, required=True, help="The input jsonl file path.")
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help=(
            "The path to the output directory if using end to end data preparation, the path to output hdf5 file if"
            " running tokenization"
        ),
    )
    parser.add_argument(
        "--overwrite_output_path",
        action="store_true",
        help="If the file or files stored at the output path can be over-written",
    )
    parser.add_argument(
        "--tokenizer_class",
        type=str,
        choices=list(TOKENIZER_CLASSES.keys()),
        default=None,
        required=False,
        help=(
            "pre-specified tokenizer class to run, defaults to gpt2, must be a choice from"
            f" {list(TOKENIZER_CLASSES.keys())}"
        ),
    )
    parser.add_argument(
        "--pretrained_tokenizer",
        default=None,
        type=str,
        required=False,
        help=(
            "The pretrained tokenizer to be used, loaded using"
            " transformers.AutoTokenizer.from_pretrained(args.pretrained_tokenizer), in lieu of a custom vocab and"
            " merges file."
        ),
    )
    parser.add_argument(
        "--vocab_file",
        default=None,
        type=str,
        required=False,
        help=(
            "The vocabulary file for the tokenizer. Should be a .json file for the tokenizer class specified by"
            " --tokenizer_class."
        ),
    )
    parser.add_argument(
        "--merges_file",
        type=str,
        default=None,
        required=False,
        help="The merges file to be used with the tokenizer class specified by --tokenizer_class.",
    )
    parser.add_argument(
        "--max_seq_length",
        default=2048,
        type=int,
        required=False,
        help=(
            "The max sequence length after tokenization. \n Sequence will be truncated or padded to this length before"
            " input into the model. Defaults to 512."
        ),
    )
    parser.add_argument(
        "--input_packing_config",
        type=PackingConfig.from_str,
        default=PackingConfig.get_default(),
        choices=PackingConfig.get_choices(),
        required=False,
        help=(
            "The first argument in the packing config defines the method of placing text into sequences, the second"
            " argument defines how to handle jsonls that do not fit within the max_seq_length. 'full': Defines the"
            " entire packing config, Completely fill sequences with tokens, as soon as sequences is full start packing"
            " into new sequence. Ignore article boundaries, they may be split across multiple sequences. 'greedy': Fit"
            " as many articles as possible into a sequence, make sure no article is split across multiple sequences."
            " Fill the left over space in each sequence with padding. 'single': Each sequence contains only 1 article. "
            " Fill the rest of the sequence with padding.  'drop': Drop the entire article if there are any tokens that"
            " overflow beyond the max sequence length.  'truncate_left':  Truncate the article from the left if there"
            " are any tokens that overflow beyond the max sequence length.  'truncate_right':  Truncate the article"
            " from the right if there are any tokens that overflow beyond the max sequence length."
        ),
    )
    parser.add_argument(
        "--packing_boundary",
        type=str,
        default=BoundaryType.JSONL.value,
        choices=BoundaryType.as_list(),
        required=False,
        help=(
            "How to define the boundary when packing jsonl into sequences. Choosing jsonl will define each jsonl as a"
            " packing unit, and keep it together. Choosing prompt_completion_pair option, defines"
            " prompt_completion_pairs as the packing unit and will keep them together, but prompt completion pairs"
            " within one jsonl may be split into multiple sequences."
        ),
    )
    parser.add_argument(
        "--attention_boundary",
        type=str,
        default=BoundaryType.JSONL.value,
        choices=BoundaryType.as_list(),
        required=False,
        help=(
            "What boundary to use when training with --article_attention flag. If you choose prompt_completion_pair"
            " tokens will only attend to tokens in the prompt_completion_pair. If you choose jsonl, then tokens will"
            " attend to all the prompt completion pairs in the jsonl"
        ),
    )
    parser.add_argument(
        "--special_tokens_dict",
        type=str,
        default=None,
        required=False,
        help="Any non-standard special tokens in JSON format to add to tokenizer. e.g. '{'sep_token': \"[SEP]\"}'",
    )
    parser.add_argument(
        "--prompt_keyword",
        default="prompt",
        type=str,
        required=False,
        help="keyword used in input json to specify prompt",
    )
    parser.add_argument(
        "--completion_keyword",
        default="completion",
        type=str,
        required=False,
        help="keyword used in input json to specify completion, defaults to 'completion",
    )

    parser.add_argument(
        "--prompt_prefix",
        default=None,
        type=str,
        required=False,
        help="Text to add before the prompt, for chatML conventions use",
    )
    parser.add_argument(
        "--prompt_postfix",
        default=None,
        type=str,
        required=False,
        help="text to add after the prompt, for chatML conventions use",
    )
    parser.add_argument(
        "--disable_space_separator",
        action="store_true",
        help=(
            "FOR ADVANCED USERS: If you include this flag, NO spaces will be appended to the completion. (If you do not"
            " add this flag then a space is added to every completion if it does not already have a space) This flag is"
            ' dangerous because if you have input data like {"prompt": hello. "completion": how are you?}, when the'
            ' prompt and completion are combined it will look like "hello.how are you?" which will mess up the'
            " tokenization."
        ),
    )
    parser.add_argument(
        "--keep_prompt_only_sequences",
        action="store_true",
        help=(
            "FOR ADVANCED USERS: If you include this flag, packed sequences with only prompt tokens will not be"
            " dropped. Data with only prompt will be dropped by default because training with prompt-only sequences"
            " with prompt_loss_weight=0.0 may lead to errors. Data is dropped because of one of the following"
            " conditions: 1. the input file data prompt completion pairs contains only a prompt. 2. If the sequence is"
            " truncated such that only prompt tokens remain"
        ),
    )
    parser.add_argument(
        "--categories_path",
        default=None,
        type=str,
        required=False,
        help=(
            "If you include this flag, then the 'category' field from your input jsonls will be stored in the"
            " 'category_id' dataset in your output hdf5 files. This flag must point to the file path of a json"
            " file that contains a list of all the strings of the 'category' keys in your dataset."
        ),
    )


def execute_and_return_stdout(command):
    """Execute [command] using os.system, and then returns the terminal outputs.

    The text can be accessed by accessing [result].stderr or [result].stdout

    Args:
        command (str): string format of linux command to execute

    Returns:
        Piped Out object: Access text using .stout or .stderr attributes of output object
    """
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)  # nosec
    return result
