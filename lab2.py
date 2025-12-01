#!/usr/bin/env python3

import argparse
import json
import os
import glob
from datetime import datetime
import sys

DATE_FORMAT = "%Y-%m-%d %H:%M"
DEFAULT_DB_JSON = "db.json"
DEFAULT_ERRORS_TXT = "errors.txt"


def is_alnum_len(value, min_len, max_len):
    return value.isalnum() and min_len <= len(value) <= max_len


def is_airport_code(value):
    return len(value) == 3 and value.isupper() and value.isalpha()


def parse_datetime(value):
    return datetime.strptime(value, DATE_FORMAT)


def validate_price(value):
    p = float(value)
    if p <= 0:
        raise ValueError("price must be positive")
    return p


def validate_flight_row(line, line_number):
    parts = line.strip().split(",")
    if len(parts) != 6:
        return None, "missing required fields"

    flight_id, origin, destination, dep_dt_str, arr_dt_str, price_str = [p.strip() for p in parts]

    errors = []

    if not is_alnum_len(flight_id, 2, 8):
        errors.append("invalid flight_id")

    if not is_airport_code(origin):
        errors.append("invalid origin")
    if not is_airport_code(destination):
        errors.append("invalid destination")

    try:
        dep_dt = parse_datetime(dep_dt_str)
    except:
        dep_dt = None
        errors.append("invalid departure_datetime")

    try:
        arr_dt = parse_datetime(arr_dt_str)
    except:
        arr_dt = None
        errors.append("invalid arrival_datetime")

    if dep_dt and arr_dt and arr_dt <= dep_dt:
        errors.append("arrival must be after departure")

    try:
        price = validate_price(price_str)
    except Exception as e:
        price = None
        errors.append(str(e))

    if errors:
        return None, "; ".join(errors)

    return {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "departure_datetime": dep_dt_str,
        "arrival_datetime": arr_dt_str,
        "price": price,
    }, None


def parse_csv_file(path, valid_flights, error_lines):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                s = line.strip()
                if s == "":
                    continue
                if line_number == 1 and "flight_id" in s:
                    continue
                if s.startswith("#"):
                    error_lines.append(f"Line {line_number}: {s} -> comment")
                    continue

                flight, err = validate_flight_row(line, line_number)
                if err:
                    error_lines.append(f"Line {line_number}: {s} -> {err}")
                else:
                    valid_flights.append(flight)
    except:
        pass


def parse_input_sources(csv_file, folder):
    valid = []
    errors = []

    if csv_file:
        parse_csv_file(csv_file, valid, errors)

    if folder:
        pattern = os.path.join(folder, "*.csv")
        for p in sorted(glob.glob(pattern)):
            parse_csv_file(p, valid, errors)

    return valid, errors


def save_db_json(flights, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flights, f, indent=4)


def save_errors_txt(error_lines, path):
    with open(path, "w", encoding="utf-8") as f:
        for line in error_lines:
            f.write(line + "\n")


def load_db_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_queries(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return [data]
    return data


def flight_matches_query(flight, q):
    if "flight_id" in q and flight["flight_id"] != q["flight_id"]:
        return False
    if "origin" in q and flight["origin"] != q["origin"]:
        return False
    if "destination" in q and flight["destination"] != q["destination"]:
        return False

    if "price" in q:
        try:
            if float(flight["price"]) > float(q["price"]):
                return False
        except:
            return False

    if "departure_datetime" in q:
        try:
            if parse_datetime(flight["departure_datetime"]) < parse_datetime(q["departure_datetime"]):
                return False
        except:
            return False

    if "arrival_datetime" in q:
        try:
            if parse_datetime(flight["arrival_datetime"]) > parse_datetime(q["arrival_datetime"]):
                return False
        except:
            return False

    return True


def build_response_filename(student_id="241ADB088",
                            first_name="Challa",
                            last_name="Navaneeth_Reddy"):
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"response_{student_id}{first_name}{last_name}_{ts}.json"


def run_queries_and_save(db, query_path, out_path=None):
    queries = load_queries(query_path)
    results = []

    for q in queries:
        matches = [f for f in db if flight_matches_query(f, q)]
        results.append({"query": q, "matches": matches})

    if out_path is None:
        out_path = build_response_filename()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)


def build_arg_parser():
    p = argparse.ArgumentParser(description="Flight Schedule Parser")
    p.add_argument("-i", "--input")
    p.add_argument("-d", "--directory")
    p.add_argument("-o", "--output")
    p.add_argument("-j", "--json-db")
    p.add_argument("-q", "--query")
    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    db = []
    used_csv = False

    if args.json_db:
        db = load_db_json(args.json_db)
    else:
        if not args.input and not args.directory:
            print("ERROR: provide -i, -d, or -j")
            sys.exit(1)

        db, errors = parse_input_sources(args.input, args.directory)
        used_csv = True

        out_json = args.output if args.output else DEFAULT_DB_JSON
        save_db_json(db, out_json)
        save_errors_txt(errors, DEFAULT_ERRORS_TXT)

    if args.query:
        run_queries_and_save(db, args.query)

    if not args.query and not used_csv:
        print("Loaded JSON DB; no queries executed.")


if  __name__ == "_main_":
    main()