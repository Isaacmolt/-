"""
SheetCraft AI — Monthly Budget Tracker Generator
Generates a professional Excel/Google Sheets budget template with:
- Dashboard, Monthly Input, Categories, Annual View, Instructions
- Full formulas, conditional formatting, charts
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.chart import PieChart, BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os

# Brand colors
BRAND_GREEN = "2D5F2D"
BRAND_CREAM = "F5F0E8"
BRAND_GOLD = "D4A574"
BRAND_DARK = "1A1A1A"
BRAND_WHITE = "FFFFFF"
BRAND_LIGHT_GREEN = "E8F0E8"
BRAND_RED = "CC4444"
BRAND_LIGHT_RED = "FFE0E0"

# Styles
HEADER_FONT = Font(name="Calibri", size=14, bold=True, color=BRAND_WHITE)
SUBHEADER_FONT = Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN)
NORMAL_FONT = Font(name="Calibri", size=11, color=BRAND_DARK)
MONEY_FORMAT = '#,##0.00'
PCT_FORMAT = '0.0%'

HEADER_FILL = PatternFill(start_color=BRAND_GREEN, end_color=BRAND_GREEN, fill_type="solid")
CREAM_FILL = PatternFill(start_color=BRAND_CREAM, end_color=BRAND_CREAM, fill_type="solid")
GOLD_FILL = PatternFill(start_color=BRAND_GOLD, end_color=BRAND_GOLD, fill_type="solid")
WHITE_FILL = PatternFill(start_color=BRAND_WHITE, end_color=BRAND_WHITE, fill_type="solid")
LIGHT_GREEN_FILL = PatternFill(start_color=BRAND_LIGHT_GREEN, end_color=BRAND_LIGHT_GREEN, fill_type="solid")

THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)

CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")
WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)


def style_header_row(ws, row, max_col):
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER
        cell.border = THIN_BORDER


def style_cell(cell, font=None, fill=None, alignment=None, number_format=None):
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if alignment:
        cell.alignment = alignment
    if number_format:
        cell.number_format = number_format
    cell.border = THIN_BORDER


def create_categories_sheet(wb):
    ws = wb.create_sheet("Categories")

    headers = ["Category", "Type", "Monthly Budget"]
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 18

    # Title
    ws.merge_cells("A1:C1")
    title_cell = ws["A1"]
    title_cell.value = "BUDGET CATEGORIES"
    style_cell(title_cell, font=Font(name="Calibri", size=16, bold=True, color=BRAND_WHITE),
               fill=HEADER_FILL, alignment=CENTER)
    for col in range(2, 4):
        style_cell(ws.cell(row=1, column=col), fill=HEADER_FILL)

    # Headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        style_cell(cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_WHITE),
                   fill=HEADER_FILL, alignment=CENTER)

    # Needs (50%)
    needs = [
        ("Rent / Mortgage", 1500),
        ("Utilities", 150),
        ("Groceries", 400),
        ("Transportation", 200),
        ("Insurance", 150),
        ("Phone / Internet", 100),
        ("Minimum Debt Payments", 200),
    ]

    wants = [
        ("Dining Out", 150),
        ("Entertainment", 100),
        ("Shopping", 150),
        ("Subscriptions", 50),
        ("Personal Care", 50),
        ("Hobbies", 100),
    ]

    savings = [
        ("Emergency Fund", 200),
        ("Investments", 200),
        ("Savings Goals", 100),
    ]

    row = 4
    for name, budget in needs:
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value="Needs")
        cell = ws.cell(row=row, column=3, value=budget)
        for c in range(1, 4):
            style_cell(ws.cell(row=row, column=c), font=NORMAL_FONT, fill=CREAM_FILL, alignment=LEFT if c < 3 else CENTER)
        cell.number_format = MONEY_FORMAT
        row += 1

    for name, budget in wants:
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value="Wants")
        cell = ws.cell(row=row, column=3, value=budget)
        for c in range(1, 4):
            style_cell(ws.cell(row=row, column=c), font=NORMAL_FONT, fill=WHITE_FILL, alignment=LEFT if c < 3 else CENTER)
        cell.number_format = MONEY_FORMAT
        row += 1

    for name, budget in savings:
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value="Savings")
        cell = ws.cell(row=row, column=3, value=budget)
        for c in range(1, 4):
            style_cell(ws.cell(row=row, column=c), font=NORMAL_FONT, fill=LIGHT_GREEN_FILL, alignment=LEFT if c < 3 else CENTER)
        cell.number_format = MONEY_FORMAT
        row += 1

    # Totals
    row += 1
    ws.cell(row=row, column=1, value="TOTAL BUDGET")
    style_cell(ws.cell(row=row, column=1), font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN),
               fill=CREAM_FILL, alignment=LEFT)
    total_cell = ws.cell(row=row, column=3)
    total_cell.value = f"=SUM(C4:C{row - 2})"
    style_cell(total_cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN),
               fill=CREAM_FILL, alignment=CENTER, number_format=MONEY_FORMAT)

    return len(needs), len(wants), len(savings)


def create_monthly_input_sheet(wb, categories_count):
    ws = wb.create_sheet("Monthly Input")

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 18

    # Title
    ws.merge_cells("A1:E1")
    title_cell = ws["A1"]
    title_cell.value = "MONTHLY EXPENSE TRACKER"
    style_cell(title_cell, font=Font(name="Calibri", size=16, bold=True, color=BRAND_WHITE),
               fill=HEADER_FILL, alignment=CENTER)
    for col in range(2, 6):
        style_cell(ws.cell(row=1, column=col), fill=HEADER_FILL)

    # Income section
    ws.merge_cells("A3:B3")
    ws["A3"].value = "MONTHLY INCOME"
    style_cell(ws["A3"], font=Font(name="Calibri", size=12, bold=True, color=BRAND_WHITE),
               fill=PatternFill(start_color=BRAND_GOLD, end_color=BRAND_GOLD, fill_type="solid"), alignment=LEFT)
    for col in range(2, 3):
        style_cell(ws.cell(row=3, column=col), fill=GOLD_FILL)

    income_items = ["Salary / Wages", "Side Income", "Investment Income", "Other Income"]
    for i, item in enumerate(income_items):
        row = 4 + i
        ws.cell(row=row, column=1, value=item)
        cell = ws.cell(row=row, column=2, value=0)
        style_cell(ws.cell(row=row, column=1), font=NORMAL_FONT, fill=CREAM_FILL, alignment=LEFT)
        style_cell(cell, font=NORMAL_FONT, fill=WHITE_FILL, alignment=CENTER, number_format=MONEY_FORMAT)

    total_income_row = 4 + len(income_items)
    ws.cell(row=total_income_row, column=1, value="TOTAL INCOME")
    style_cell(ws.cell(row=total_income_row, column=1),
               font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN), fill=LIGHT_GREEN_FILL, alignment=LEFT)
    total_cell = ws.cell(row=total_income_row, column=2)
    total_cell.value = f"=SUM(B4:B{total_income_row - 1})"
    style_cell(total_cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN),
               fill=LIGHT_GREEN_FILL, alignment=CENTER, number_format=MONEY_FORMAT)

    # Expense transaction log
    expense_start = total_income_row + 2
    headers = ["Date", "Description", "Amount", "Category", "Notes"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=expense_start, column=col, value=header)
        style_cell(cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_WHITE),
                   fill=HEADER_FILL, alignment=CENTER)

    # Sample data rows
    sample_data = [
        ("2026-01-01", "Monthly Rent", 1500, "Rent / Mortgage", ""),
        ("2026-01-03", "Grocery Store", 85.50, "Groceries", "Weekly groceries"),
        ("2026-01-05", "Electric Bill", 65.00, "Utilities", ""),
        ("2026-01-07", "Restaurant", 45.00, "Dining Out", "Dinner with friends"),
        ("2026-01-10", "Gas Station", 50.00, "Transportation", ""),
    ]

    for i, (date, desc, amount, category, notes) in enumerate(sample_data):
        row = expense_start + 1 + i
        ws.cell(row=row, column=1, value=date)
        ws.cell(row=row, column=2, value=desc)
        ws.cell(row=row, column=3, value=amount)
        ws.cell(row=row, column=4, value=category)
        ws.cell(row=row, column=5, value=notes)
        for col in range(1, 6):
            fill = CREAM_FILL if i % 2 == 0 else WHITE_FILL
            style_cell(ws.cell(row=row, column=col), font=NORMAL_FONT, fill=fill,
                       alignment=CENTER if col == 3 else LEFT)
        ws.cell(row=row, column=3).number_format = MONEY_FORMAT

    # Add 95 empty rows for user input
    for i in range(len(sample_data), 100):
        row = expense_start + 1 + i
        for col in range(1, 6):
            fill = CREAM_FILL if i % 2 == 0 else WHITE_FILL
            style_cell(ws.cell(row=row, column=col), font=NORMAL_FONT, fill=fill, alignment=LEFT)

    return total_income_row, expense_start


def create_dashboard(wb, income_row, expense_start_row):
    ws = wb.create_sheet("Dashboard")

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 18
    ws.column_dimensions["G"].width = 5

    # Title
    ws.merge_cells("B1:F1")
    ws["B1"].value = "MONTHLY BUDGET DASHBOARD"
    style_cell(ws["B1"], font=Font(name="Calibri", size=20, bold=True, color=BRAND_WHITE),
               fill=HEADER_FILL, alignment=CENTER)
    for col in range(3, 7):
        style_cell(ws.cell(row=1, column=col), fill=HEADER_FILL)

    ws.merge_cells("B2:F2")
    ws["B2"].value = "Your Financial Overview at a Glance"
    style_cell(ws["B2"], font=Font(name="Calibri", size=11, italic=True, color=BRAND_GREEN),
               fill=CREAM_FILL, alignment=CENTER)
    for col in range(3, 7):
        style_cell(ws.cell(row=2, column=col), fill=CREAM_FILL)

    # Summary Cards Row
    cards = [
        ("Total Income", f"='Monthly Input'!B{income_row}", BRAND_GREEN),
        ("Total Expenses", f"=SUM('Monthly Input'!C{expense_start_row + 1}:C{expense_start_row + 100})", BRAND_RED),
        ("Remaining", f"=C4-D4", BRAND_GREEN),
        ("Savings Rate", f"=IF(C4>0,F4/C4,0)", BRAND_GOLD),
    ]

    # Card headers
    row = 3
    for col_idx, (label, _, color) in enumerate(cards):
        col = col_idx + 3  # C, D, E, F
        cell = ws.cell(row=row, column=col, value=label)
        style_cell(cell, font=Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
                   fill=PatternFill(start_color=color, end_color=color, fill_type="solid"),
                   alignment=CENTER)

    # Card values
    row = 4
    for col_idx, (_, formula, _) in enumerate(cards):
        col = col_idx + 3
        cell = ws.cell(row=row, column=col, value=formula)
        fmt = PCT_FORMAT if col_idx == 3 else MONEY_FORMAT
        style_cell(cell, font=Font(name="Calibri", size=16, bold=True, color=BRAND_DARK),
                   fill=CREAM_FILL, alignment=CENTER, number_format=fmt)

    # Category breakdown
    row = 6
    ws.merge_cells(f"B{row}:F{row}")
    ws[f"B{row}"].value = "SPENDING BY CATEGORY"
    style_cell(ws[f"B{row}"], font=Font(name="Calibri", size=14, bold=True, color=BRAND_WHITE),
               fill=HEADER_FILL, alignment=CENTER)
    for col in range(3, 7):
        style_cell(ws.cell(row=row, column=col), fill=HEADER_FILL)

    row = 7
    cat_headers = ["Category", "Budget", "Actual", "Remaining", "% Used"]
    for col, header in enumerate(cat_headers, 2):
        cell = ws.cell(row=row, column=col, value=header)
        style_cell(cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN),
                   fill=LIGHT_GREEN_FILL, alignment=CENTER)

    categories = [
        "Rent / Mortgage", "Utilities", "Groceries", "Transportation",
        "Insurance", "Phone / Internet", "Minimum Debt Payments",
        "Dining Out", "Entertainment", "Shopping", "Subscriptions",
        "Personal Care", "Hobbies", "Emergency Fund", "Investments", "Savings Goals"
    ]

    for i, cat in enumerate(categories):
        r = 8 + i
        cat_row_in_categories = 4 + i

        ws.cell(row=r, column=2, value=cat)
        # Budget from Categories sheet
        ws.cell(row=r, column=3, value=f"=Categories!C{cat_row_in_categories}")
        # Actual: SUMIF from Monthly Input
        ws.cell(row=r, column=4,
                value=f"=SUMIF('Monthly Input'!D{expense_start_row + 1}:D{expense_start_row + 100},B{r},'Monthly Input'!C{expense_start_row + 1}:C{expense_start_row + 100})")
        # Remaining
        ws.cell(row=r, column=5, value=f"=C{r}-D{r}")
        # % Used
        ws.cell(row=r, column=6, value=f"=IF(C{r}>0,D{r}/C{r},0)")

        fill = CREAM_FILL if i % 2 == 0 else WHITE_FILL
        for col in range(2, 7):
            cell = ws.cell(row=r, column=col)
            fmt = MONEY_FORMAT if col in (3, 4, 5) else (PCT_FORMAT if col == 6 else None)
            style_cell(cell, font=NORMAL_FONT, fill=fill, alignment=CENTER if col > 2 else LEFT,
                       number_format=fmt)

    # Conditional formatting: over budget = red
    last_cat_row = 8 + len(categories) - 1
    ws.conditional_formatting.add(
        f"E8:E{last_cat_row}",
        CellIsRule(operator="lessThan", formula=["0"],
                   fill=PatternFill(start_color=BRAND_LIGHT_RED, end_color=BRAND_LIGHT_RED, fill_type="solid"),
                   font=Font(color=BRAND_RED, bold=True))
    )
    ws.conditional_formatting.add(
        f"F8:F{last_cat_row}",
        CellIsRule(operator="greaterThan", formula=["1"],
                   fill=PatternFill(start_color=BRAND_LIGHT_RED, end_color=BRAND_LIGHT_RED, fill_type="solid"),
                   font=Font(color=BRAND_RED, bold=True))
    )

    # Pie chart — spending by category
    pie = PieChart()
    pie.title = "Spending Distribution"
    pie.style = 10
    cats = Reference(ws, min_col=2, min_row=8, max_row=last_cat_row)
    data = Reference(ws, min_col=4, min_row=7, max_row=last_cat_row)
    pie.add_data(data, titles_from_data=True)
    pie.set_categories(cats)
    pie.width = 18
    pie.height = 12
    ws.add_chart(pie, f"B{last_cat_row + 3}")

    # Bar chart — budget vs actual
    bar = BarChart()
    bar.type = "col"
    bar.title = "Budget vs Actual"
    bar.style = 10
    bar.y_axis.title = "Amount ($)"
    budget_data = Reference(ws, min_col=3, min_row=7, max_row=last_cat_row)
    actual_data = Reference(ws, min_col=4, min_row=7, max_row=last_cat_row)
    bar.add_data(budget_data, titles_from_data=True)
    bar.add_data(actual_data, titles_from_data=True)
    bar.set_categories(cats)
    bar.width = 22
    bar.height = 12
    ws.add_chart(bar, f"B{last_cat_row + 20}")


def create_annual_view(wb, income_row, expense_start_row):
    ws = wb.create_sheet("Annual View")

    ws.column_dimensions["A"].width = 18
    for col in range(2, 14):
        ws.column_dimensions[get_column_letter(col)].width = 14
    ws.column_dimensions["N"].width = 16

    # Title
    ws.merge_cells("A1:N1")
    ws["A1"].value = "ANNUAL FINANCIAL OVERVIEW 2026"
    style_cell(ws["A1"], font=Font(name="Calibri", size=16, bold=True, color=BRAND_WHITE),
               fill=HEADER_FILL, alignment=CENTER)
    for col in range(2, 15):
        style_cell(ws.cell(row=1, column=col), fill=HEADER_FILL)

    # Month headers
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "TOTAL"]
    ws.cell(row=3, column=1, value="")
    for i, month in enumerate(months):
        cell = ws.cell(row=3, column=i + 2, value=month)
        style_cell(cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_WHITE),
                   fill=HEADER_FILL, alignment=CENTER)

    # Rows
    rows_data = ["Total Income", "Total Expenses", "Net Savings", "Savings Rate"]
    for r_idx, label in enumerate(rows_data):
        row = 4 + r_idx
        ws.cell(row=row, column=1, value=label)
        style_cell(ws.cell(row=row, column=1),
                   font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN),
                   fill=CREAM_FILL, alignment=LEFT)

        for col in range(2, 14):
            cell = ws.cell(row=row, column=col, value=0)
            fmt = PCT_FORMAT if r_idx == 3 else MONEY_FORMAT
            fill = LIGHT_GREEN_FILL if r_idx == 2 else (CREAM_FILL if col % 2 == 0 else WHITE_FILL)
            style_cell(cell, font=NORMAL_FONT, fill=fill, alignment=CENTER, number_format=fmt)

        # Total column
        col_letter_start = get_column_letter(2)
        col_letter_end = get_column_letter(13)
        total_cell = ws.cell(row=row, column=14)
        if r_idx == 3:
            total_cell.value = f"=IF(N4>0,N6/N4,0)"
        else:
            total_cell.value = f"=SUM({col_letter_start}{row}:{col_letter_end}{row})"
        fmt = PCT_FORMAT if r_idx == 3 else MONEY_FORMAT
        style_cell(total_cell, font=Font(name="Calibri", size=11, bold=True, color=BRAND_GREEN),
                   fill=LIGHT_GREEN_FILL, alignment=CENTER, number_format=fmt)

    # Net Savings formula
    for col in range(2, 14):
        ws.cell(row=6, column=col, value=f"={get_column_letter(col)}4-{get_column_letter(col)}5")
        ws.cell(row=7, column=col, value=f"=IF({get_column_letter(col)}4>0,{get_column_letter(col)}6/{get_column_letter(col)}4,0)")

    # Bar chart for annual trend
    bar = BarChart()
    bar.type = "col"
    bar.title = "Monthly Income vs Expenses"
    bar.style = 10
    bar.y_axis.title = "Amount ($)"
    cats = Reference(ws, min_col=2, max_col=13, min_row=3)
    income_data = Reference(ws, min_col=2, max_col=13, min_row=4)
    expense_data = Reference(ws, min_col=2, max_col=13, min_row=5)
    bar.add_data(income_data, from_rows=True, titles_from_data=False)
    bar.add_data(expense_data, from_rows=True, titles_from_data=False)
    bar.set_categories(cats)
    bar.series[0].title = openpyxl.chart.series.SeriesLabel(v="Income")
    bar.series[1].title = openpyxl.chart.series.SeriesLabel(v="Expenses")
    bar.width = 24
    bar.height = 14
    ws.add_chart(bar, "A10")


def create_instructions_sheet(wb):
    ws = wb.create_sheet("Instructions")

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 80

    ws.merge_cells("B1:B1")
    ws["B1"].value = "HOW TO USE YOUR BUDGET TRACKER"
    style_cell(ws["B1"], font=Font(name="Calibri", size=18, bold=True, color=BRAND_WHITE),
               fill=HEADER_FILL, alignment=CENTER)

    instructions = [
        ("Getting Started", [
            "1. Go to the 'Categories' tab first",
            "2. Customize the category names and budget amounts to match your needs",
            "3. Go to 'Monthly Input' and enter your monthly income at the top",
            "4. Start entering your daily expenses in the transaction log",
            "5. Check your 'Dashboard' to see your spending overview!",
        ]),
        ("Tips for Best Results", [
            "- Enter expenses as soon as they happen (or at end of each day)",
            "- Be specific with descriptions (e.g., 'Walmart groceries' not just 'store')",
            "- Review your Dashboard weekly to stay on track",
            "- Adjust your budgets monthly based on actual spending patterns",
            "- Use the Annual View to track your progress over the year",
        ]),
        ("Customization", [
            "- You can change category names in the Categories tab",
            "- Adjust budget amounts anytime — formulas update automatically",
            "- Add new categories by inserting rows (keep same format)",
            "- Change colors: Format → Alternating colors in Google Sheets",
        ]),
        ("Important Notes", [
            "- DO NOT delete or rename sheet tabs (formulas will break)",
            "- DO NOT modify cells with formulas (they calculate automatically)",
            "- Make a backup copy before major changes (File → Make a copy)",
            "- Formula cells are in GREEN — those are automatic!",
        ]),
        ("Need Help?", [
            "If you have any questions or issues, please message us on Etsy.",
            "We're happy to help you get the most out of your budget tracker!",
            "",
            "Thank you for your purchase! ★★★★★",
        ]),
    ]

    row = 3
    for section_title, items in instructions:
        ws.cell(row=row, column=2, value=section_title)
        style_cell(ws.cell(row=row, column=2),
                   font=Font(name="Calibri", size=13, bold=True, color=BRAND_GREEN),
                   fill=LIGHT_GREEN_FILL, alignment=LEFT)
        row += 1

        for item in items:
            ws.cell(row=row, column=2, value=item)
            style_cell(ws.cell(row=row, column=2), font=NORMAL_FONT, fill=WHITE_FILL, alignment=WRAP)
            ws.row_dimensions[row].height = 22
            row += 1

        row += 1


def generate():
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Create sheets in order
    n_needs, n_wants, n_savings = create_categories_sheet(wb)
    income_row, expense_start_row = create_monthly_input_sheet(wb, n_needs + n_wants + n_savings)
    create_dashboard(wb, income_row, expense_start_row)
    create_annual_view(wb, income_row, expense_start_row)
    create_instructions_sheet(wb)

    # Reorder: Dashboard first
    sheet_order = ["Dashboard", "Monthly Input", "Categories", "Annual View", "Instructions"]
    for i, name in enumerate(sheet_order):
        wb.move_sheet(name, offset=i - wb.sheetnames.index(name))

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "Monthly_Budget_Tracker_SheetCraft.xlsx")
    wb.save(output_path)
    print(f"Template generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate()
