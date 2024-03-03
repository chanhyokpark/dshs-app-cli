from tabulate import tabulate


def display_tables_horizontally(tables, headers=[], tablefmt="fancy_grid", spacing=3):
    """Displays multiple tables horizontally using string manipulation.

    Args:
        tables: A list of data lists, where each data list represents a table.
        headers: An optional list of headers for each table.
        tablefmt: The tabulate table format.
        spacing: Number of spaces between tables.
    """

    table_strs = [
        tabulate(table, headers=headers, tablefmt=tablefmt) for table in tables
    ]
    max_lines = max(table_str.count("\n") for table_str in table_strs)

    output_lines = []
    for i in range(max_lines + 1):
        line = ""
        for table_str in table_strs:
            lines = table_str.splitlines()
            line += lines[i] if i < len(lines) else ""
            line += " " * spacing
        output_lines.append(line.rstrip())  # Remove trailing spaces

    result = "\n".join(output_lines)
    print(result)


def print_table(data, vertical=False):  # 3d 배열
    str_tables = []
    for t in data:
        str_tables.append(
            tabulate(
                t,
                headers=[],
                tablefmt="fancy_grid",
                numalign="center",
                stralign="center",
            )
        )
    if vertical:
        print(("\n" * 2).join(str_tables))
    else:
        max_r = max((len(d) for d in data)) + 3
        c = tuple(len(d.split("\n")[0]) for d in str_tables)
        s = "\n" * max_r
        for i, t in enumerate(str_tables):
            sp = t.split("\n")
            for j in range(max_r):
                if len(sp) > j:
                    s = s.replace("\n", sp[j] + " " * 3 + "*", 1)
                else:
                    s = s.replace("\n", " " * (c[i] + 3) + "*", 1)
            s = s.replace("*", "\n")
        print(s)


def center_multiline_string(s):
    # Split the string into lines
    lines = s.split("\n")

    # Find the length of the longest line
    max_width = max(len(line) for line in lines)

    # Center each line and add necessary padding for lines with odd lengths
    centered_lines = [line.center(max_width + (len(line) % 2)) for line in lines]

    # Join the centered lines back into a single string
    return "\n".join(centered_lines)


# Example Usage
# data1 = [[1, 2, center_multiline_string("s102\nsfsdfs\n12")]]
data1 = [[1, 2, "s102\n1604\n박찬혁"]]
data2 = [[5, 6], [7, 8]]
data3 = [[9, 10, 11], [12, 13, 14]]
tables = [data1, data2, data3]
print_table(tables)
