"""
SheetCraft AI — Product 05: 50/30/20 Budget Template
Agent: 阿比
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os

G="2D5F2D";C="F5F0E8";D="1A1A1A";W="FFFFFF";LG="E8F0E8";R="CC4444";LR="FFE0E0";GO="D4A574"
GF=PatternFill(start_color=G,end_color=G,fill_type="solid")
CF=PatternFill(start_color=C,end_color=C,fill_type="solid")
WF=PatternFill(start_color=W,end_color=W,fill_type="solid")
LGF=PatternFill(start_color=LG,end_color=LG,fill_type="solid")
NF=Font(name="Calibri",size=11,color=D)
TB=Border(left=Side(style="thin",color="CCCCCC"),right=Side(style="thin",color="CCCCCC"),top=Side(style="thin",color="CCCCCC"),bottom=Side(style="thin",color="CCCCCC"))
CT=Alignment(horizontal="center",vertical="center")
LT=Alignment(horizontal="left",vertical="center")
WR=Alignment(horizontal="left",vertical="top",wrap_text=True)
MF='#,##0.00';PF='0.0%'

def sc(cell,font=None,fill=None,align=None,nf=None):
    if font:cell.font=font
    if fill:cell.fill=fill
    if align:cell.alignment=align
    if nf:cell.number_format=nf
    cell.border=TB

def title_row(ws,row,text,mc):
    ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=mc)
    cell=ws.cell(row=row,column=1,value=text)
    sc(cell,Font(name="Calibri",size=18,bold=True,color=W),GF,CT)
    for c in range(2,mc+1):sc(ws.cell(row=row,column=c),fill=GF)

def hdr(ws,row,headers):
    for i,h in enumerate(headers,1):
        sc(ws.cell(row=row,column=i,value=h),Font(name="Calibri",size=11,bold=True,color=W),GF,CT)

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,8):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"50 / 30 / 20 BUDGET DASHBOARD",7)
    # Income input
    ws.cell(row=3,column=1,value="Monthly Income:");sc(ws.cell(row=3,column=1),Font(name="Calibri",size=12,bold=True,color=G),CF,LT)
    ws.cell(row=3,column=2,value=5000);sc(ws.cell(row=3,column=2),Font(name="Calibri",size=16,bold=True,color=D),CF,CT,MF)
    # Auto splits
    splits=[("NEEDS (50%)","=B3*0.5",f"=Needs!B3"),("WANTS (30%)","=B3*0.3",f"=Wants!B3"),("SAVINGS (20%)","=B3*0.2",f"=Savings!B3")]
    for i,(label,target,actual) in enumerate(splits):
        r=5+i*2
        ws.cell(row=r,column=1,value=label);sc(ws.cell(row=r,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
        ws.cell(row=r,column=2,value="Target");sc(ws.cell(row=r,column=2),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=r,column=3,value=target);sc(ws.cell(row=r,column=3),Font(name="Calibri",size=13,bold=True,color=G),CF,CT,MF)
        ws.cell(row=r,column=4,value="Actual");sc(ws.cell(row=r,column=4),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=r,column=5,value=actual);sc(ws.cell(row=r,column=5),Font(name="Calibri",size=13,bold=True,color=D),CF,CT,MF)
        ws.cell(row=r,column=6,value="Remaining");sc(ws.cell(row=r,column=6),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=r,column=7).value=f"=C{r}-E{r}";sc(ws.cell(row=r,column=7),Font(name="Calibri",size=13,bold=True,color=D),CF,CT,MF)
    # Conditional formatting on remaining
    for r in [5,7,9]:
        ws.conditional_formatting.add(f"G{r}",CellIsRule(operator="lessThan",formula=["0"],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
        ws.conditional_formatting.add(f"G{r}",CellIsRule(operator="greaterThanOrEqual",formula=["0"],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    # Pie chart
    ws.cell(row=12,column=1,value="Needs");ws.cell(row=12,column=2).value="=E5"
    ws.cell(row=13,column=1,value="Wants");ws.cell(row=13,column=2).value="=E7"
    ws.cell(row=14,column=1,value="Savings");ws.cell(row=14,column=2).value="=E9"
    for r in range(12,15):sc(ws.cell(row=r,column=1),NF,CF,LT);sc(ws.cell(row=r,column=2),NF,CF,CT,MF)
    pie=PieChart();pie.title="Actual Allocation";pie.style=10
    cats=Reference(ws,min_col=1,min_row=12,max_row=14)
    data=Reference(ws,min_col=2,min_row=11,max_row=14)
    pie.add_data(data,titles_from_data=True);pie.set_categories(cats);pie.width=14;pie.height=10
    ws.add_chart(pie,"A16")

def create_needs(wb):
    ws=wb.create_sheet("Needs")
    cols=["Date","Description","Amount","Subcategory"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"NEEDS (50%) — Essential Expenses",len(cols))
    ws.cell(row=2,column=1,value="Total Spent:");sc(ws.cell(row=2,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=2,column=2).value="=SUM(C5:C104)";sc(ws.cell(row=2,column=2),Font(name="Calibri",size=14,bold=True,color=D),LGF,CT,MF)
    ws.cell(row=2,column=3,value="Budget:");sc(ws.cell(row=2,column=3),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=2,column=4).value="=Dashboard!B3*0.5";sc(ws.cell(row=2,column=4),Font(name="Calibri",size=14,bold=True,color=G),LGF,CT,MF)
    hdr(ws,4,cols)
    sample=[("2026-01-01","Rent",1500,"Rent/Mortgage"),("2026-01-03","Electric Bill",85,"Utilities"),("2026-01-03","Water Bill",45,"Utilities"),("2026-01-05","Groceries",120,"Groceries"),("2026-01-08","Gas",45,"Transportation"),("2026-01-10","Phone Bill",65,"Utilities"),("2026-01-12","Groceries",95,"Groceries"),("2026-01-15","Health Insurance",200,"Insurance"),("2026-01-18","Bus Pass",50,"Transportation"),("2026-01-20","Groceries",110,"Groceries")]
    for i,(date,desc,amt,sub) in enumerate(sample):
        r=5+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,desc,amt,sub],1):
            ws.cell(row=r,column=c,value=v)
            sc(ws.cell(row=r,column=c),NF,fill,CT if c==3 else LT,MF if c==3 else None)
    for i in range(len(sample),100):
        r=5+i;fill=CF if i%2==0 else WF
        for c in range(1,5):sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_wants(wb):
    ws=wb.create_sheet("Wants")
    cols=["Date","Description","Amount","Subcategory"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"WANTS (30%) — Lifestyle & Fun",len(cols))
    ws.cell(row=2,column=1,value="Total Spent:");sc(ws.cell(row=2,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=2,column=2).value="=SUM(C5:C104)";sc(ws.cell(row=2,column=2),Font(name="Calibri",size=14,bold=True,color=D),LGF,CT,MF)
    ws.cell(row=2,column=3,value="Budget:");sc(ws.cell(row=2,column=3),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=2,column=4).value="=Dashboard!B3*0.3";sc(ws.cell(row=2,column=4),Font(name="Calibri",size=14,bold=True,color=G),LGF,CT,MF)
    hdr(ws,4,cols)
    sample=[("2026-01-02","Coffee Shop",5.50,"Dining Out"),("2026-01-04","Netflix",15.99,"Subscriptions"),("2026-01-06","Restaurant Dinner",65,"Dining Out"),("2026-01-09","Movie Tickets",28,"Entertainment"),("2026-01-11","Spotify",10.99,"Subscriptions"),("2026-01-14","New Shoes",89,"Shopping"),("2026-01-17","Happy Hour",35,"Dining Out"),("2026-01-22","Book",18,"Shopping")]
    for i,(date,desc,amt,sub) in enumerate(sample):
        r=5+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,desc,amt,sub],1):
            ws.cell(row=r,column=c,value=v)
            sc(ws.cell(row=r,column=c),NF,fill,CT if c==3 else LT,MF if c==3 else None)
    for i in range(len(sample),100):
        r=5+i;fill=CF if i%2==0 else WF
        for c in range(1,5):sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_savings(wb):
    ws=wb.create_sheet("Savings")
    cols=["Date","Description","Amount","Destination"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"SAVINGS (20%) — Future You",len(cols))
    ws.cell(row=2,column=1,value="Total Saved:");sc(ws.cell(row=2,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=2,column=2).value="=SUM(C5:C104)";sc(ws.cell(row=2,column=2),Font(name="Calibri",size=14,bold=True,color=D),LGF,CT,MF)
    ws.cell(row=2,column=3,value="Target:");sc(ws.cell(row=2,column=3),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=2,column=4).value="=Dashboard!B3*0.2";sc(ws.cell(row=2,column=4),Font(name="Calibri",size=14,bold=True,color=G),LGF,CT,MF)
    hdr(ws,4,cols)
    sample=[("2026-01-01","Emergency Fund",400,"Emergency Fund"),("2026-01-01","401k Contribution",500,"Retirement"),("2026-01-15","Index Fund",100,"Investments")]
    for i,(date,desc,amt,dest) in enumerate(sample):
        r=5+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,desc,amt,dest],1):
            ws.cell(row=r,column=c,value=v)
            sc(ws.cell(row=r,column=c),NF,fill,CT if c==3 else LT,MF if c==3 else None)
    for i in range(len(sample),100):
        r=5+i;fill=CF if i%2==0 else WF
        for c in range(1,5):sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_monthly_summary(wb):
    ws=wb.create_sheet("Monthly Summary")
    cols=["Month","Income","Needs","Wants","Savings","Needs %","Wants %","Savings %","Status"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=14
    title_row(ws,1,"MONTHLY SUMMARY",len(cols))
    hdr(ws,3,cols)
    months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    sample_data=[(5000,2315,267.48,1000),(5000,2400,1350,1000),(5200,2500,1400,1050),(5000,0,0,0),(5000,0,0,0),(5000,0,0,0),(5000,0,0,0),(5000,0,0,0),(5200,0,0,0),(5000,0,0,0),(5500,0,0,0),(6000,0,0,0)]
    for i,(m) in enumerate(months):
        r=4+i;fill=CF if i%2==0 else WF
        inc,needs,wants,sav=sample_data[i]
        ws.cell(row=r,column=1,value=m);ws.cell(row=r,column=2,value=inc);ws.cell(row=r,column=3,value=needs);ws.cell(row=r,column=4,value=wants);ws.cell(row=r,column=5,value=sav)
        ws.cell(row=r,column=6).value=f"=IF(B{r}>0,C{r}/B{r},0)"
        ws.cell(row=r,column=7).value=f"=IF(B{r}>0,D{r}/B{r},0)"
        ws.cell(row=r,column=8).value=f"=IF(B{r}>0,E{r}/B{r},0)"
        ws.cell(row=r,column=9).value=f'=IF(B{r}=0,"—",IF(AND(F{r}<=0.55,G{r}<=0.35,H{r}>=0.15),"On Track","Over Budget"))'
        for c in range(1,10):
            fmt=MF if c in(2,3,4,5) else(PF if c in(6,7,8) else None)
            sc(ws.cell(row=r,column=c),NF,fill,CT,fmt)
    lr=15
    ws.conditional_formatting.add(f"I4:I{lr}",CellIsRule(operator="equal",formula=['"On Track"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"I4:I{lr}",CellIsRule(operator="equal",formula=['"Over Budget"'],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
    bar=BarChart();bar.type="col";bar.title="Monthly Allocation";bar.style=10
    cats=Reference(ws,min_col=1,min_row=4,max_row=15)
    for col in [3,4,5]:
        data=Reference(ws,min_col=col,min_row=3,max_row=15)
        bar.add_data(data,titles_from_data=True)
    bar.set_categories(cats);bar.width=22;bar.height=12
    ws.add_chart(bar,"A18")

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE THE 50/30/20 BUDGET",2)
    items=[("The 50/30/20 Rule",["50% NEEDS: Essential expenses you can't avoid (rent, food, bills)","30% WANTS: Lifestyle spending (dining, entertainment, shopping)","20% SAVINGS: Building your future (emergency fund, investments, debt payoff)"]),
           ("Getting Started",["1. Enter your monthly income on the Dashboard","2. Log needs expenses in the 'Needs' tab","3. Log wants expenses in the 'Wants' tab","4. Log savings/investments in the 'Savings' tab","5. Dashboard updates automatically!"]),
           ("Tips",["- Check Dashboard weekly to stay on track","- If Needs > 50%, look for ways to reduce fixed costs","- If Wants > 30%, find free/cheap alternatives","- Always pay yourself first (automate savings!)","- Update Monthly Summary at end of each month"]),
           ("Need Help?",["Message us on Etsy!","The 50/30/20 rule is a guideline — adjust to fit YOUR life!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:
            ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_dashboard(wb);create_needs(wb);create_wants(wb);create_savings(wb);create_monthly_summary(wb);create_instructions(wb)
    order=["Dashboard","Needs","Wants","Savings","Monthly Summary","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"503020_Budget_Template_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out

if __name__=="__main__":generate()
