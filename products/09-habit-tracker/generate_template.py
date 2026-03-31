"""SheetCraft AI — Product 09: Annual Habit Tracker. Agent: 小習"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os, calendar
G="2D5F2D";C="F5F0E8";D="1A1A1A";W="FFFFFF";LG="E8F0E8";R="CC4444";LR="FFE0E0"
GF=PatternFill(start_color=G,end_color=G,fill_type="solid");CF=PatternFill(start_color=C,end_color=C,fill_type="solid")
WF=PatternFill(start_color=W,end_color=W,fill_type="solid");LGF=PatternFill(start_color=LG,end_color=LG,fill_type="solid")
NF=Font(name="Calibri",size=11,color=D)
SF=Font(name="Calibri",size=10,color=D)
TB=Border(left=Side(style="thin",color="CCCCCC"),right=Side(style="thin",color="CCCCCC"),top=Side(style="thin",color="CCCCCC"),bottom=Side(style="thin",color="CCCCCC"))
CT=Alignment(horizontal="center",vertical="center");LT=Alignment(horizontal="left",vertical="center");WR=Alignment(horizontal="left",vertical="top",wrap_text=True)
PF='0.0%'
HABITS=["Exercise","Read 30min","Meditate","Drink 2L water","No phone before bed","Save $5","Journal","Learn new skill"]

def sc(cell,font=None,fill=None,align=None,nf=None):
    if font:cell.font=font
    if fill:cell.fill=fill
    if align:cell.alignment=align
    if nf:cell.number_format=nf
    cell.border=TB
def title_row(ws,row,text,mc):
    ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=mc)
    sc(ws.cell(row=row,column=1,value=text),Font(name="Calibri",size=16,bold=True,color=W),GF,CT)
    for c in range(2,mc+1):sc(ws.cell(row=row,column=c),fill=GF)

def create_habit_setup(wb):
    ws=wb.create_sheet("Habit Setup")
    cols=["Habit","Category","Frequency","Weekly Goal","Start Date","Why"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"HABIT SETUP",len(cols))
    for i,h in enumerate(cols,1):sc(ws.cell(row=3,column=i,value=h),Font(name="Calibri",size=11,bold=True,color=W),GF,CT)
    data=[("Exercise","Health","Daily",7,"2026-01-01","Stay fit and healthy"),
          ("Read 30min","Learning","Daily",7,"2026-01-01","Read 24 books this year"),
          ("Meditate","Health","Daily",7,"2026-01-01","Mental clarity"),
          ("Drink 2L water","Health","Daily",7,"2026-01-01","Stay hydrated"),
          ("No phone before bed","Productivity","Daily",7,"2026-01-01","Better sleep"),
          ("Save $5","Financial","Daily",7,"2026-01-01","Build emergency fund"),
          ("Journal","Productivity","Daily",5,"2026-01-01","Self reflection"),
          ("Learn new skill","Learning","Weekly",3,"2026-01-01","Career growth")]
    for i,(habit,cat,freq,goal,start,why) in enumerate(data):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([habit,cat,freq,goal,start,why],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,CT if c in(3,4) else LT)

def create_month_sheet(wb,month_num,year=2026):
    import random
    month_name=calendar.month_name[month_num]
    days=calendar.monthrange(year,month_num)[1]
    ws=wb.create_sheet(month_name[:3])
    ws.column_dimensions["A"].width=22
    for c in range(2,days+4):ws.column_dimensions[get_column_letter(c)].width=4
    ws.column_dimensions[get_column_letter(days+2)].width=10
    ws.column_dimensions[get_column_letter(days+3)].width=10
    title_row(ws,1,f"{month_name.upper()} {year}",days+3)
    # Day headers
    for d in range(1,days+1):
        sc(ws.cell(row=3,column=d+1,value=d),Font(name="Calibri",size=9,bold=True,color=W),GF,CT)
    sc(ws.cell(row=3,column=days+2,value="Done"),Font(name="Calibri",size=9,bold=True,color=W),GF,CT)
    sc(ws.cell(row=3,column=days+3,value="Rate"),Font(name="Calibri",size=9,bold=True,color=W),GF,CT)
    sc(ws.cell(row=3,column=1,value="Habit"),Font(name="Calibri",size=11,bold=True,color=W),GF,CT)
    for hi,habit in enumerate(HABITS):
        r=4+hi;fill=CF if hi%2==0 else WF
        ws.cell(row=r,column=1,value=habit);sc(ws.cell(row=r,column=1),NF,fill,LT)
        for d in range(1,days+1):
            cell=ws.cell(row=r,column=d+1)
            if month_num==1:
                cell.value=1 if random.random()>0.3 else 0
            sc(cell,SF,fill,CT)
        # Done count
        col_start=get_column_letter(2);col_end=get_column_letter(days+1)
        ws.cell(row=r,column=days+2).value=f"=SUM(B{r}:{get_column_letter(days+1)}{r})"
        sc(ws.cell(row=r,column=days+2),Font(name="Calibri",size=10,bold=True,color=G),LGF,CT)
        ws.cell(row=r,column=days+3).value=f"=IF({days}>0,{get_column_letter(days+2)}{r}/{days},0)"
        sc(ws.cell(row=r,column=days+3),Font(name="Calibri",size=10,bold=True,color=G),LGF,CT,PF)
    # Conditional formatting for 1/0
    lr=4+len(HABITS)-1
    cell_range=f"B4:{get_column_letter(days+1)}{lr}"
    ws.conditional_formatting.add(cell_range,CellIsRule(operator="equal",formula=["1"],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,size=9)))
    ws.conditional_formatting.add(cell_range,CellIsRule(operator="equal",formula=["0"],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,size=9)))

def create_annual_summary(wb):
    ws=wb.create_sheet("Annual Summary")
    months_short=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ws.column_dimensions["A"].width=22
    for c in range(2,15):ws.column_dimensions[get_column_letter(c)].width=10
    title_row(ws,1,"ANNUAL HABIT SUMMARY 2026",14)
    headers=["Habit"]+months_short+["Average"]
    for i,h in enumerate(headers,1):sc(ws.cell(row=3,column=i,value=h),Font(name="Calibri",size=11,bold=True,color=W),GF,CT)
    for hi,habit in enumerate(HABITS):
        r=4+hi;fill=CF if hi%2==0 else WF
        ws.cell(row=r,column=1,value=habit);sc(ws.cell(row=r,column=1),NF,fill,LT)
        for mi,m in enumerate(months_short):
            # Reference each month's rate column for this habit
            if m in [s.title for s in wb.sheetnames if len(s)==3]:
                month_ws=wb[m]
                rate_col=month_ws.max_column
                ws.cell(row=r,column=mi+2).value=f"=IF(ISBLANK('{m}'!{get_column_letter(rate_col)}{r}),0,'{m}'!{get_column_letter(rate_col)}{r})"
            else:
                ws.cell(row=r,column=mi+2,value=0)
            sc(ws.cell(row=r,column=mi+2),NF,fill,CT,PF)
        ws.cell(row=r,column=14).value=f"=AVERAGE(B{r}:M{r})"
        sc(ws.cell(row=r,column=14),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,PF)
    lr=4+len(HABITS)-1
    ws.conditional_formatting.add(f"B4:N{lr}",CellIsRule(operator="greaterThanOrEqual",formula=["0.8"],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"B4:N{lr}",CellIsRule(operator="lessThan",formula=["0.5"],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R)))
    bar=BarChart();bar.type="col";bar.title="Average Completion Rate by Habit";bar.style=10
    cats=Reference(ws,min_col=1,min_row=4,max_row=lr)
    data=Reference(ws,min_col=14,min_row=3,max_row=lr)
    bar.add_data(data,titles_from_data=True);bar.set_categories(cats);bar.width=20;bar.height=12
    ws.add_chart(bar,f"A{lr+3}")

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,7):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"HABIT TRACKER DASHBOARD",6)
    ws.cell(row=3,column=2,value="Active Habits");sc(ws.cell(row=3,column=2),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
    ws.cell(row=4,column=2,value=len(HABITS));sc(ws.cell(row=4,column=2),Font(name="Calibri",size=20,bold=True,color=D),CF,CT)
    ws.cell(row=3,column=4,value="Overall Rate (Jan)");sc(ws.cell(row=3,column=4),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
    ws.cell(row=4,column=4).value="=AVERAGE(Jan!AF4:AF11)";sc(ws.cell(row=4,column=4),Font(name="Calibri",size=20,bold=True,color=G),CF,CT,PF)
    ws.cell(row=6,column=2,value="Tip: Fill in 1 (done) or 0 (missed) each day.");sc(ws.cell(row=6,column=2),Font(name="Calibri",size=11,italic=True,color=G),CF,LT)
    ws.merge_cells("B6:E6")

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR HABIT TRACKER",2)
    items=[("Getting Started",["1. Review habits in 'Habit Setup' — customize as needed","2. Go to the current month tab (Jan, Feb, etc.)","3. Each day, enter 1 (completed) or 0 (missed)","4. Completion rate calculates automatically","5. Check 'Annual Summary' for year-long trends"]),
           ("Color Guide",["GREEN cell = habit completed (1)","RED cell = habit missed (0)","Annual Summary: GREEN >= 80%, RED < 50%"]),
           ("Tips",["- Fill in your tracker at the same time each day","- Start with 3-4 habits, add more once consistent","- Don't break the chain! Streaks build momentum","- Review Annual Summary monthly to spot trends"]),
           ("Need Help?",["Message us on Etsy!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_habit_setup(wb)
    for m in range(1,13):create_month_sheet(wb,m)
    create_annual_summary(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Habit Setup"]+[calendar.month_name[m][:3] for m in range(1,13)]+["Annual Summary","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Annual_Habit_Tracker_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out
if __name__=="__main__":generate()
