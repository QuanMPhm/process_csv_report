import sys
import argparse
import pydantic
import yaml
import logging

from process_report.institute_list_models import InstituteList


def pydantic_to_github(err, institute_list_file):
    """Produce a github error annotation from a pydantic ValidationError"""
    for error in err.errors():
        print(
            f"::error file={institute_list_file},title=Validation error::{error['msg']}"
        )


def yaml_to_github(err, institute_list_file):
    """Produce a github error annotation from a YAML ParserError"""
    line = err.problem_mark.line
    print(
        f"::error file={institute_list_file},line={line},title=Parser error::{err.context}: {err.problem}"
    )


def main(arg_list: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-g", "--github", action="store_true", help="Emit github workflow annotations"
    )
    parser.add_argument(
        "institute_list", default="process_report/institute_list.yaml", nargs="?"
    )
    args = parser.parse_args(arg_list)

    try:
        with open(args.institute_list) as f:
            data = yaml.safe_load(f)
            institute_list = InstituteList.model_validate(data)
            logging.info(
                f"Validation of {len(institute_list.root)} institution entries successful"
            )
    except pydantic.ValidationError as err:
        if args.github:
            pydantic_to_github(err, args.institute_list)
        sys.exit(err)
    except yaml.parser.ParserError as err:
        if args.github:
            yaml_to_github(err, args.institute_list)
        sys.exit(err)


if __name__ == "__main__":
    main()
