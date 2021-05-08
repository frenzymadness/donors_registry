def get_part_of_line(line, delimiter=";"):
    try:
        del_index = line.index(delimiter)
        return line[:del_index], line[del_index + 1 :]
    except ValueError:
        return line, ""


def is_line_valid(line):
    parts = line.split(";")
    if not parts[-1]:
        # If the last part of the line is empty we can skip the line entirely.
        # Line ending  with semicolon means that the donor has 0 dotations.
        return None

    if len(parts) == 8 and all(parts):
        return True
    else:
        return False


def repair_two_semicolons(line):
    repaired_line = line
    while ";;" in repaired_line:
        repaired_line = repaired_line.replace(";;", ";")
    return repaired_line


def repair_line_part_by_part(line):  # noqa: C901 FIXME
    errors = []
    rodne_cislo, rest = get_part_of_line(line)
    if not rodne_cislo:
        errors.append("chybí rodné číslo")
    elif not rodne_cislo.isnumeric():
        errors.append("rodné číslo není číselné")
    elif len(rodne_cislo) > 10:
        errors.append("rodné číslo je příliš dlouhé")
    elif len(rodne_cislo) < 9:
        errors.append("rodné číslo je příliš krátké")

    first_name, rest = get_part_of_line(rest)
    if not first_name:
        errors.append("chybí jméno")

    last_name, rest = get_part_of_line(rest)
    if not last_name:
        errors.append("chybí příjmení")

    address, rest = get_part_of_line(rest)
    if not address:
        errors.append("chybí ulice")

    city, rest = get_part_of_line(rest)
    if not city:
        errors.append("chybí město")

    postal_code, rest = get_part_of_line(rest)
    if not postal_code:
        postal_code = "00000"
        errors.append("chybí PSČ, nahrazeno nulami")

    kod_pojistovny, rest = get_part_of_line(rest)
    if not kod_pojistovny:
        kod_pojistovny = "000"
        errors.append("chybí pojišťovna, nahrazena nulami")

    donation_count, rest = get_part_of_line(rest)
    if not donation_count or not donation_count.isnumeric():
        errors.append("počet odběrů není číselný")

    repaired_line = ";".join(
        [
            rodne_cislo,
            first_name,
            last_name,
            address,
            city,
            postal_code,
            kod_pojistovny,
            donation_count,
        ]
    )

    return repaired_line, errors


def validate_import_data(text_input):
    valid_lines = []  # List of valid lines (strings)
    invalid_lines = []  # List of tuples (line, list of comments)
    for line in text_input.splitlines():
        if is_line_valid(line) is None:
            # None means we should skip the line because the donations count
            # is not present at the end of the line
            continue

        if ";;" in line:
            repaired_line = repair_two_semicolons(line)
            if is_line_valid(repaired_line):
                invalid_lines.append(
                    (repaired_line, ["řádek obsahoval dvojici středníků"])
                )
                continue

        repaired_line, errors = repair_line_part_by_part(line)
        if errors or not is_line_valid(line):
            invalid_lines.append((repaired_line, errors))
        else:
            valid_lines.append(line)

    return valid_lines, invalid_lines
