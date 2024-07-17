#! /usr/bin/env python3

# Generate a BOM from a PrjPcb file.
# For more information, read the README file in this directory.

import argparse
import csv
import os
import yaml
import sys
from contextlib import ExitStack

from allspice import AllSpice
from allspice.utils.bom_generation import generate_bom, ColumnConfig


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="generate_bom", description="Generate a BOM from a project repository."
    )
    parser.add_argument(
        "repository", help="The repo containing the project in the form 'owner/repo'"
    )
    parser.add_argument(
        "source_file",
        help=(
            "The path to the source file used to generate the BOM. If this is an Altium project, "
            "this should be the .PrjPcb file. For an OrCAD project, this should be the .dsn file. "
            "Example: 'Archimajor.PrjPcb', 'Schematics/Beagleplay.dsn'."
        ),
    )
    parser.add_argument(
        "--columns",
        help=(
            "A path to a YAML file mapping columns to the attributes they are from. See the README "
            "for more details. Defaults to 'columns.yml'."
        ),
        default="columns.yml",
    )
    parser.add_argument(
        "--source_ref",
        help=(
            "The git reference the BOM should be generated for (eg. branch name, tag name, commit "
            "SHA). Defaults to the main branch."
        ),
        default="main",
    )
    parser.add_argument(
        "--allspice_hub_url",
        help="The URL of your AllSpice Hub instance. Defaults to https://hub.allspice.io.",
    )
    parser.add_argument(
        "--output_file",
        help="The path to the output file. If absent, the CSV will be output to the command line.",
    )
    parser.add_argument(
        "--group_by",
        help=(
            "A comma-separated list of columns to group the BOM by. If not present, the BOM will "
            "be flat."
        ),
    )
    parser.add_argument(
        "--variant",
        help=(
            "The variant of the project to generate the BOM for. If not present, the BOM will be "
            "generated for the default variant. This is not used for OrCAD projects."
        ),
    )

    args = parser.parse_args()

    columns_file = args.columns
    columns = {}
    try:
        with open(columns_file, "r") as f:
            columns_data = yaml.safe_load(f.read())
            for column_value in columns_data["columns"]:
                column_config = {}
                column_config["attributes"] = column_value["part_attributes"]
                if "sort" in column_value:
                    column_config["sort"] = ColumnConfig.SortOrder(column_value["sort"])
                if "remove_rows_matching" in column_value:
                    column_config["remove_rows_matching"] = column_value["remove_rows_matching"]
                if "grouped_values_sort" in column_value:
                    column_config["grouped_values_sort"] = ColumnConfig.SortOrder(
                        column_value["grouped_values_sort"]
                    )
                if "grouped_values_separator" in column_value:
                    column_config["grouped_values_separator"] = column_value[
                        "grouped_values_separator"
                    ]
                if "grouped_values_allow_duplicates" in column_value:
                    column_config["grouped_values_allow_duplicates"] = column_value[
                        "grouped_values_allow_duplicates"
                    ]
                columns[column_value["name"]] = ColumnConfig(**column_config)
    except KeyError as e:
        print(f"Error: columns file {columns_file} does not seem to be in the right format.")
        print("Please refer to the README for more information.")
        print(f"Caused by: {e}")
        sys.exit(1)

    auth_token = os.environ.get("ALLSPICE_AUTH_TOKEN")
    if auth_token is None:
        print("Please set the environment variable ALLSPICE_AUTH_TOKEN")
        exit(1)

    if args.allspice_hub_url is None:
        allspice = AllSpice(token_text=auth_token)
    else:
        allspice = AllSpice(token_text=auth_token, allspice_hub_url=args.allspice_hub_url)

    repo_owner, repo_name = args.repository.split("/")
    repository = allspice.get_repository(repo_owner, repo_name)
    group_by = args.group_by.split(",") if args.group_by else None

    print("Generating BOM...", file=sys.stderr)

    bom_rows = generate_bom(
        allspice,
        repository,
        args.source_file,
        columns,
        group_by=group_by,
        ref=args.source_ref if args.source_ref else "main",
        variant=args.variant if args.variant else None,
    )

    with ExitStack() as stack:
        keys = bom_rows[0].keys()
        if args.output_file is not None:
            f = stack.enter_context(open(args.output_file, "w"))
            writer = csv.DictWriter(f, fieldnames=keys)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=keys)

        writer.writeheader()
        writer.writerows(bom_rows)

    print("Generated bom.", file=sys.stderr)
