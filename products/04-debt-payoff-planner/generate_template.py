"""
SheetCraft AI — Product 04: Debt Payoff Planner
Agent: 小雪
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os

G="2D5F2D";C="F5F0E8";D="1A1A1A";W="FFFFFF";LG="E8F0E8";R="CC4444";LR="FFE0E0";GO="D4A574"
GF=PatternFill(start_color=G,end_color=G,fill_type="solid")
CF=PatternFill(start_color=C,end_color=C,fill_type="solid")
WF=PatternFill(start_color=W,end_color=W,fill_type="solid")
LGF=PatternFill(start_color=LG,end_color=LG,fill_type="solid")
RF=PatternFill(start_color=R,end_color=R,fill_type="solid")
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

def create_debt_inventory(wb):
    ws=wb.create_sheet("Debt Inventory")
    cols=["Debt Name","Type","Balance","APR %","Min Payment","Due Date"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"DEBT INVENTORY",len(cols))
    hdr(ws,3,cols)
    debts=[
        ("Chase Credit Card","Credit Card",4500,22.99,135,"15th"),
        ("Student Loan","Student Loan",18000,5.50,250,"1st"),
        ("Car Loan","Auto Loan",12000,6.25,350,"10th"),
        ("Amex Card","Credit Card",2200,19.99,66,"20th"),
        ("Personal Loan","Personal",5000,9.00,150,"5th"),
    ]
    for i,(name,dtype,bal,apr,minp,due) in enumerate(debts):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([name,dtype,bal,apr,minp,due],1):
            ws.cell(row=r,column=c,value=v)
            fmt=MF if c in(3,5) else (PF if c==4 else None)
            if c==4:ws.cell(row=r,column=c).value=apr/100;ws.cell(row=r,column=c).number_format=PF
            else:pass
            sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,fmt)
        ws.cell(row=r,column=4).value=apr/100
        ws.cell(row=r,column=4).number_format='0.00%'
    tr=4+len(debts)
    ws.cell(row=tr,column=1,value="TOTALS")
    ws.cell(row=tr,column=3).value=f"=SUM(C4:C{tr-1})"
    ws.cell(row=tr,column=5).value=f"=SUM(E4:E{tr-1})"
    for c in range(1,7):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c in(3,5) else None)
    return debts

def create_snowball(wb,debts):
    ws=wb.create_sheet("Snowball Method")
    ws.column_dimensions["A"].width=22;ws.column_dimensions["B"].width=16;ws.column_dimensions["C"].width=16;ws.column_dimensions["D"].width=16;ws.column_dimensions["E"].width=16
    title_row(ws,1,"SNOWBALL METHOD (Smallest Balance First)",5)
    ws.cell(row=2,column=1,value="Extra monthly payment:");sc(ws.cell(row=2,column=1),Font(name="Calibri",size=11,bold=True,color=G),CF,LT)
    ws.cell(row=2,column=2,value=300);sc(ws.cell(row=2,column=2),Font(name="Calibri",size=14,bold=True,color=D),CF,CT,MF)
    sorted_debts=sorted(debts,key=lambda x:x[2])
    hdr(ws,4,["Debt Name","Starting Balance","Min Payment","Priority","Focus Order"])
    for i,(name,_,bal,apr,minp,_) in enumerate(sorted_debts):
        r=5+i;fill=LGF if i==0 else(CF if i%2==0 else WF)
        ws.cell(row=r,column=1,value=name);ws.cell(row=r,column=2,value=bal);ws.cell(row=r,column=3,value=minp)
        ws.cell(row=r,column=4,value=f"#{i+1}");ws.cell(row=r,column=5,value="FOCUS NOW" if i==0 else "Minimum")
        for c in range(1,6):sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,MF if c in(2,3) else None)
    if sorted_debts:
        sc(ws.cell(row=5,column=5),Font(name="Calibri",size=11,bold=True,color=W),PatternFill(start_color=GO,end_color=GO,fill_type="solid"),CT)
    r=5+len(sorted_debts)+1
    ws.cell(row=r,column=1,value="STRATEGY:");sc(ws.cell(row=r,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=r,column=2,value="Pay minimum on all debts. Put extra $300 toward the smallest balance first.");sc(ws.cell(row=r,column=2),NF,LGF,Alignment(horizontal="left",vertical="center",wrap_text=True))
    ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=5)

def create_avalanche(wb,debts):
    ws=wb.create_sheet("Avalanche Method")
    ws.column_dimensions["A"].width=22;ws.column_dimensions["B"].width=16;ws.column_dimensions["C"].width=16;ws.column_dimensions["D"].width=16;ws.column_dimensions["E"].width=16
    title_row(ws,1,"AVALANCHE METHOD (Highest Interest First)",5)
    ws.cell(row=2,column=1,value="Extra monthly payment:");sc(ws.cell(row=2,column=1),Font(name="Calibri",size=11,bold=True,color=G),CF,LT)
    ws.cell(row=2,column=2,value=300);sc(ws.cell(row=2,column=2),Font(name="Calibri",size=14,bold=True,color=D),CF,CT,MF)
    sorted_debts=sorted(debts,key=lambda x:x[3],reverse=True)
    hdr(ws,4,["Debt Name","Starting Balance","APR","Priority","Focus Order"])
    for i,(name,_,bal,apr,minp,_) in enumerate(sorted_debts):
        r=5+i;fill=LGF if i==0 else(CF if i%2==0 else WF)
        ws.cell(row=r,column=1,value=name);ws.cell(row=r,column=2,value=bal)
        ws.cell(row=r,column=3,value=apr/100);ws.cell(row=r,column=3).number_format='0.00%'
        ws.cell(row=r,column=4,value=f"#{i+1}");ws.cell(row=r,column=5,value="FOCUS NOW" if i==0 else "Minimum")
        for c in range(1,6):sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,MF if c==2 else None)
    if sorted_debts:
        sc(ws.cell(row=5,column=5),Font(name="Calibri",size=11,bold=True,color=W),PatternFill(start_color=GO,end_color=GO,fill_type="solid"),CT)
    r=5+len(sorted_debts)+1
    ws.cell(row=r,column=1,value="STRATEGY:");sc(ws.cell(row=r,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=r,column=2,value="Pay minimum on all debts. Put extra $300 toward the highest interest rate first. Saves more money over time.");sc(ws.cell(row=r,column=2),NF,LGF,Alignment(horizontal="left",vertical="center",wrap_text=True))
    ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=5)

def create_payment_log(wb):
    ws=wb.create_sheet("Payment Log")
    cols=["Date","Debt Name","Amount Paid","Remaining Balance","Cumulative Paid"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"PAYMENT LOG",len(cols))
    hdr(ws,3,cols)
    payments=[
        ("2026-01-15","Chase Credit Card",435,4065,435),
        ("2026-01-01","Student Loan",250,17750,685),
        ("2026-01-10","Car Loan",350,11650,1035),
        ("2026-01-20","Amex Card",66,2134,1101),
        ("2026-01-05","Personal Loan",150,4850,1251),
        ("2026-02-15","Chase Credit Card",435,3630,1686),
        ("2026-02-01","Student Loan",250,17500,1936),
        ("2026-02-10","Car Loan",350,11300,2286),
        ("2026-02-20","Amex Card",66,2068,2352),
        ("2026-02-05","Personal Loan",150,4700,2502),
    ]
    for i,(date,name,amt,rem,cum) in enumerate(payments):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,name,amt,rem,cum],1):
            ws.cell(row=r,column=c,value=v)
            sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,MF if c in(3,4,5) else None)
    # Empty rows for user input
    for i in range(len(payments),60):
        r=4+i;fill=CF if i%2==0 else WF
        for c in range(1,6):sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_comparison(wb):
    ws=wb.create_sheet("Comparison")
    ws.column_dimensions["A"].width=25;ws.column_dimensions["B"].width=20;ws.column_dimensions["C"].width=20
    title_row(ws,1,"SNOWBALL vs AVALANCHE COMPARISON",3)
    hdr(ws,3,["Metric","Snowball","Avalanche"])
    metrics=[("Total Debt",41700,41700),("Monthly Min Payments",951,951),("Extra Monthly Payment",300,300),("Est. Total Paid",47200,46100),("Est. Total Interest",5500,4400),("Est. Months to Payoff",38,36),("Interest Saved vs Other","—","$1,100")]
    for i,(metric,snow,aval) in enumerate(metrics):
        r=4+i;fill=CF if i%2==0 else WF
        ws.cell(row=r,column=1,value=metric);ws.cell(row=r,column=2,value=snow);ws.cell(row=r,column=3,value=aval)
        for c in range(1,4):
            fmt=MF if c>1 and isinstance([metric,snow,aval][c-1],(int,float)) and [metric,snow,aval][c-1]>100 else None
            sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,fmt)
    bar=BarChart();bar.type="col";bar.title="Snowball vs Avalanche";bar.style=10
    cats=Reference(ws,min_col=1,min_row=7,max_row=8)
    d1=Reference(ws,min_col=2,min_row=6,max_row=8)
    d2=Reference(ws,min_col=3,min_row=6,max_row=8)
    bar.add_data(d1,titles_from_data=True);bar.add_data(d2,titles_from_data=True)
    bar.set_categories(cats);bar.width=18;bar.height=12
    ws.add_chart(bar,"A12")

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,8):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"DEBT PAYOFF DASHBOARD",7)
    cards=[("Total Debt","='Debt Inventory'!C9"),("Monthly Payments","='Debt Inventory'!E9"),("# of Debts","5"),("Paid So Far","2502")]
    for i,(label,formula) in enumerate(cards):
        col=i*2+1
        ws.cell(row=3,column=col,value=label);sc(ws.cell(row=3,column=col),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=4,column=col,value=formula);sc(ws.cell(row=4,column=col),Font(name="Calibri",size=16,bold=True,color=D),CF,CT,MF)
        for c2 in [col+1]:sc(ws.cell(row=3,column=c2),fill=GF);sc(ws.cell(row=4,column=c2),fill=CF)
    ws.cell(row=6,column=1,value="Progress");sc(ws.cell(row=6,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    ws.cell(row=6,column=2,value="=D4/(D4+'Debt Inventory'!C9)");sc(ws.cell(row=6,column=2),Font(name="Calibri",size=14,bold=True,color=G),LGF,CT,PF)
    ws.cell(row=8,column=1,value="Recommended: Avalanche Method");sc(ws.cell(row=8,column=1),Font(name="Calibri",size=12,bold=True,color=GO),CF,LT)
    ws.merge_cells("A8:D8")
    ws.cell(row=9,column=1,value="Saves ~$1,100 in interest vs Snowball method");sc(ws.cell(row=9,column=1),NF,CF,LT)
    ws.merge_cells("A9:D9")
    pie=PieChart();pie.title="Debt Breakdown";pie.style=10
    ws.cell(row=11,column=1,value="Chase CC");ws.cell(row=11,column=2,value=4500)
    ws.cell(row=12,column=1,value="Student Loan");ws.cell(row=12,column=2,value=18000)
    ws.cell(row=13,column=1,value="Car Loan");ws.cell(row=13,column=2,value=12000)
    ws.cell(row=14,column=1,value="Amex Card");ws.cell(row=14,column=2,value=2200)
    ws.cell(row=15,column=1,value="Personal Loan");ws.cell(row=15,column=2,value=5000)
    for r in range(11,16):sc(ws.cell(row=r,column=1),NF,CF,LT);sc(ws.cell(row=r,column=2),NF,CF,CT,MF)
    cats=Reference(ws,min_col=1,min_row=11,max_row=15)
    data=Reference(ws,min_col=2,min_row=10,max_row=15)
    pie.add_data(data,titles_from_data=True);pie.set_categories(cats);pie.width=16;pie.height=10
    ws.add_chart(pie,"A17")

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR DEBT PAYOFF PLANNER",2)
    items=[("Getting Started",["1. Enter all your debts in 'Debt Inventory'","2. Review Snowball vs Avalanche methods","3. Choose your strategy and set your extra payment amount","4. Log every payment in 'Payment Log'","5. Watch your progress on the Dashboard!"]),
           ("Snowball vs Avalanche",["SNOWBALL: Pay smallest balance first → quick wins, motivation boost","AVALANCHE: Pay highest interest first → saves more money overall","Both work! Choose what keeps you motivated."]),
           ("Tips",["- Even $50 extra/month makes a huge difference","- Celebrate each debt you pay off!","- Don't take on new debt while paying off existing ones","- Consider balance transfer cards for high-interest debt"]),
           ("Need Help?",["Message us on Etsy!","You've got this — every payment brings you closer to debt-free!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:
            ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    debts=create_debt_inventory(wb);create_snowball(wb,debts);create_avalanche(wb,debts)
    create_payment_log(wb);create_comparison(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Debt Inventory","Snowball Method","Avalanche Method","Payment Log","Comparison","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Debt_Payoff_Planner_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out

if __name__=="__main__":generate()
