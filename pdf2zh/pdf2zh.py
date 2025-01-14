#!/usr/bin/env python3
"""A command line tool for extracting text and images from PDF and
output it to plain text, html, xml or tags.
"""

from __future__ import annotations

import argparse
import logging
import sys
from string import Template
from typing import List, Optional

from pdf2zh import __version__, log
from pdf2zh.high_level import translate
from pdf2zh.doclayout import OnnxModel, ModelInstance
import os

from pdf2zh.config import ConfigManager


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, add_help=True)
    parser.add_argument(
        "files",
        type=str,
        default=None,
        nargs="*",
        help="One or more paths to PDF files.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"pdf2zh v{__version__}",
    )
    parser.add_argument(
        "--debug",
        "-d",
        default=False,
        action="store_true",
        help="Use debug logging level.",
    )
    parse_params = parser.add_argument_group(
        "Parser",
        description="Used during PDF parsing",
    )
    parse_params.add_argument(
        "--pages",
        "-p",
        type=str,
        help="The list of page numbers to parse.",
    )
    parse_params.add_argument(
        "--vfont",
        "-f",
        type=str,
        default="",
        help="The regex to math font name of formula.",
    )
    parse_params.add_argument(
        "--vchar",
        "-c",
        type=str,
        default="",
        help="The regex to math character of formula.",
    )
    parse_params.add_argument(
        "--lang-in",
        "-li",
        type=str,
        default="en",
        help="The code of source language.",
    )
    parse_params.add_argument(
        "--lang-out",
        "-lo",
        type=str,
        default="zh",
        help="The code of target language.",
    )
    parse_params.add_argument(
        "--service",
        "-s",
        type=str,
        default="google",
        help="The service to use for translation.",
    )
    parse_params.add_argument(
        "--output",
        "-o",
        type=str,
        default="",
        help="Output directory for files.",
    )
    parse_params.add_argument(
        "--thread",
        "-t",
        type=int,
        default=4,
        help="The number of threads to execute translation.",
    )
    parse_params.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interact with GUI.",
    )
    parse_params.add_argument(
        "--share",
        action="store_true",
        help="Enable Gradio Share",
    )
    parse_params.add_argument(
        "--flask",
        action="store_true",
        help="flask",
    )
    parse_params.add_argument(
        "--celery",
        action="store_true",
        help="celery",
    )
    parse_params.add_argument(
        "--authorized",
        type=str,
        nargs="+",
        help="user name and password.",
    )
    parse_params.add_argument(
        "--prompt",
        type=str,
        help="user custom prompt.",
    )

    parse_params.add_argument(
        "--compatible",
        "-cp",
        action="store_true",
        help="Convert the PDF file into PDF/A format to improve compatibility.",
    )

    parse_params.add_argument(
        "--onnx",
        type=str,
        help="custom onnx model path.",
    )

    parse_params.add_argument(
        "--serverport",
        type=int,
        help="custom WebUI port.",
    )

    parse_params.add_argument(
        "--dir",
        action="store_true",
        help="translate directory.",
    )

    parse_params.add_argument(
        "--config",
        type=str,
        help="config file.",
    )

    parse_params.add_argument(
        "--electron",
        action="store_true",
    )

    parse_params.add_argument(
        "--dry_run",
        action="store_true",
    )

    return parser


def parse_args(args: Optional[List[str]]) -> argparse.Namespace:
    parsed_args = create_parser().parse_args(args=args)

    if parsed_args.pages:
        pages = []
        for p in parsed_args.pages.split(","):
            if "-" in p:
                start, end = p.split("-")
                pages.extend(range(int(start) - 1, int(end)))
            else:
                pages.append(int(p) - 1)
        parsed_args.pages = pages

    return parsed_args


def find_all_files_in_directory(directory_path):
    """
    Recursively search all PDF files in the given directory and return their paths as a list.

    :param directory_path: str, the path to the directory to search
    :return: list of PDF file paths
    """
    # Check if the provided path is a directory
    if not os.path.isdir(directory_path):
        raise ValueError(f"The provided path '{directory_path}' is not a directory.")

    file_paths = []

    # Walk through the directory recursively
    for root, _, files in os.walk(directory_path):
        for file in files:
            # Check if the file is a PDF
            if file.lower().endswith(".pdf"):
                # Append the full file path to the list
                file_paths.append(os.path.join(root, file))

    return file_paths


def dry_run():
    # 定义文件路径
    base_dir = os.getcwd()  # 获取当前路径
    config_dir = os.path.join(base_dir, "userdata")
    config_file = os.path.join(config_dir, "config.json")

    # 确保目录存在
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)  # 创建目录
        ConfigManager.custome_config(config_file)

    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        ConfigManager.get("gradio_port", 12366)
        pdf2zh_path = os.path.join(base_dir, "pdf2zh_dist", "Scripts", "pdf2zh.exe")
        if os.path.exists(pdf2zh_path):
            ConfigManager.get("pdf2zh_path", pdf2zh_path)
        else:
            import shutil

            pdf2zh_path = shutil.which("pdf2zh")
            if pdf2zh_path:
                ConfigManager.get("pdf2zh_path", pdf2zh_path)
            else:
                raise ValueError("pdf2zh not found.")


def main(args: Optional[List[str]] = None) -> int:
    logging.basicConfig()

    parsed_args = parse_args(args)

    if parsed_args.dry_run:
        dry_run()
        return 0

    if parsed_args.config:
        ConfigManager.custome_config(parsed_args.config)

    if parsed_args.debug:
        log.setLevel(logging.DEBUG)

    if parsed_args.onnx:
        ModelInstance.value = OnnxModel(parsed_args.onnx)
    else:
        ModelInstance.value = OnnxModel.load_available()

    if parsed_args.interactive:
        from pdf2zh.gui import setup_gui

        if not parsed_args.electron:
            if parsed_args.serverport:
                setup_gui(
                    parsed_args.share,
                    parsed_args.authorized,
                    int(parsed_args.serverport),
                )
            else:
                setup_gui(parsed_args.share, parsed_args.authorized)
        else:
            setup_gui(parsed_args.share, parsed_args.authorized, electron=True)
        return 0

    if parsed_args.flask:
        from pdf2zh.backend import flask_app

        flask_app.run(port=11008)
        return 0

    if parsed_args.celery:
        from pdf2zh.backend import celery_app

        celery_app.start(argv=sys.argv[2:])
        return 0

    if parsed_args.prompt:
        try:
            with open(parsed_args.prompt, "r", encoding="utf-8") as file:
                content = file.read()
            parsed_args.prompt = Template(content)
        except Exception:
            raise ValueError("prompt error.")

    print(parsed_args)
    if parsed_args.dir:
        untranlate_file = find_all_files_in_directory(parsed_args.files[0])
        parsed_args.files = untranlate_file
        translate(model=ModelInstance.value, **vars(parsed_args))
        return 0

    translate(model=ModelInstance.value, **vars(parsed_args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
