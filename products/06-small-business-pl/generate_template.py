"""
SheetCraft AI — Product 06: Small Business P&L
Agent: 老王
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
NF=Font(name="Calibri",size=11,color=D)
TB=Border(left=Side(style="thin",color="CCCCCC"),right=Side(style="thin",color="CCCCCC"),top=Side(style="thin",color="CCCCCC"),bottom=Side(style="thin",color="CCCCCC"))
CT=Alignment(horizontal="center",vertical="center");LT=Alignment(horizontal="left",vertical="center");WR=Alignment(horizontal="left",vertical="top",wrap_text=True)
MF='#,##0.00';PF='0.0%'
def sc(cell,font=None,fill=None,align=None,nf=None):
    if font:cell.font=font
    if fill:cell.fill=fill
    if align:cell.alignment=align
    if nf:cell.number_format=nf
    cell.border=TB
def title_row(ws,row,text,mc):
    ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=mc)
    sc(ws.cell(row=row,column=1,value=text),Font(name="Calibri",size=18,bold=True,color=W),GF,CT)
    for c in range(2,mc+1):sc(ws.cell(row=row,column=c),fill=GF)
def hdr(ws,row,headers):
    for i,h in enumerate(headers,1):sc(ws.cell(row=row,column=i,value=h),Font(name="Calibri",size=11,bold=True,color=W),GF,CT)

def create_monthly_pl(wb):
    ws=wb.create_sheet("Monthly P&L")
    ws.column_dimensions["A"].width=28
    for c in range(2,15):ws.column_dimensions[get_column_letter(c)].width=14
    title_row(ws,1,"PROFIT & LOSS STATEMENT",14)
    months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","TOTAL"]
    hdr(ws,3,["Category"]+months)
    # Revenue
    r=4;ws.cell(row=r,column=1,value="REVENUE");sc(ws.cell(row=r,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    for c in range(2,15):sc(ws.cell(row=r,column=c),fill=LGF)
    rev_items=[("Product Sales",[8000,9500,11000,0,0,0,0,0,0,0,0,0]),("Service Revenue",[5000,5000,6000,0,0,0,0,0,0,0,0,0]),("Other Income",[500,300,800,0,0,0,0,0,0,0,0,0])]
    for ri,(name,vals) in enumerate(rev_items):
        r=5+ri;fill=CF if ri%2==0 else WF
        ws.cell(row=r,column=1,value=name);sc(ws.cell(row=r,column=1),NF,fill,LT)
        for mi,v in enumerate(vals):ws.cell(row=r,column=mi+2,value=v);sc(ws.cell(row=r,column=mi+2),NF,fill,CT,MF)
        ws.cell(row=r,column=14).value=f"=SUM(B{r}:M{r})";sc(ws.cell(row=r,column=14),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF)
    tr=8;ws.cell(row=tr,column=1,value="TOTAL REVENUE");sc(ws.cell(row=tr,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    for c in range(2,15):ws.cell(row=tr,column=c).value=f"=SUM({get_column_letter(c)}5:{get_column_letter(c)}7)";sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF)
    # COGS
    r=10;ws.cell(row=r,column=1,value="COST OF GOODS SOLD");sc(ws.cell(row=r,column=1),Font(name="Calibri",size=11,bold=True,color=D),CF,LT)
    for c in range(2,15):sc(ws.cell(row=r,column=c),fill=CF)
    cogs=[("Materials/Supplies",[2000,2500,3000,0,0,0,0,0,0,0,0,0]),("Direct Labor",[1500,1500,1800,0,0,0,0,0,0,0,0,0])]
    for ri,(name,vals) in enumerate(cogs):
        r=11+ri;fill=CF if ri%2==0 else WF
        ws.cell(row=r,column=1,value=name);sc(ws.cell(row=r,column=1),NF,fill,LT)
        for mi,v in enumerate(vals):ws.cell(row=r,column=mi+2,value=v);sc(ws.cell(row=r,column=mi+2),NF,fill,CT,MF)
        ws.cell(row=r,column=14).value=f"=SUM(B{r}:M{r})";sc(ws.cell(row=r,column=14),NF,CF,CT,MF)
    tcr=13;ws.cell(row=tcr,column=1,value="TOTAL COGS");sc(ws.cell(row=tcr,column=1),Font(name="Calibri",size=11,bold=True,color=D),CF,LT)
    for c in range(2,15):ws.cell(row=tcr,column=c).value=f"=SUM({get_column_letter(c)}11:{get_column_letter(c)}12)";sc(ws.cell(row=tcr,column=c),Font(name="Calibri",size=11,bold=True,color=D),CF,CT,MF)
    # Gross Profit
    gpr=14;ws.cell(row=gpr,column=1,value="GROSS PROFIT");sc(ws.cell(row=gpr,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    for c in range(2,15):ws.cell(row=gpr,column=c).value=f"={get_column_letter(c)}8-{get_column_letter(c)}13";sc(ws.cell(row=gpr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF)
    # Operating Expenses
    r=16;ws.cell(row=r,column=1,value="OPERATING EXPENSES");sc(ws.cell(row=r,column=1),Font(name="Calibri",size=11,bold=True,color=R),PatternFill(start_color=LR,end_color=LR,fill_type="solid"),LT)
    for c in range(2,15):sc(ws.cell(row=r,column=c),fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"))
    opex=[("Rent",[2000]*3+[0]*9),("Utilities",[300]*3+[0]*9),("Payroll",[3000]*3+[0]*9),("Marketing",[800,1000,1200]+[0]*9),("Software/Tools",[200]*3+[0]*9),("Insurance",[350]*3+[0]*9),("Office Supplies",[150,100,200]+[0]*9),("Professional Services",[500,0,750]+[0]*9),("Travel",[200,0,400]+[0]*9),("Miscellaneous",[100,150,100]+[0]*9)]
    for ri,(name,vals) in enumerate(opex):
        r=17+ri;fill=CF if ri%2==0 else WF
        ws.cell(row=r,column=1,value=name);sc(ws.cell(row=r,column=1),NF,fill,LT)
        for mi,v in enumerate(vals):ws.cell(row=r,column=mi+2,value=v);sc(ws.cell(row=r,column=mi+2),NF,fill,CT,MF)
        ws.cell(row=r,column=14).value=f"=SUM(B{r}:M{r})";sc(ws.cell(row=r,column=14),NF,CF,CT,MF)
    toer=27;ws.cell(row=toer,column=1,value="TOTAL OPERATING EXPENSES");sc(ws.cell(row=toer,column=1),Font(name="Calibri",size=11,bold=True,color=R),PatternFill(start_color=LR,end_color=LR,fill_type="solid"),LT)
    for c in range(2,15):ws.cell(row=toer,column=c).value=f"=SUM({get_column_letter(c)}17:{get_column_letter(c)}26)";sc(ws.cell(row=toer,column=c),Font(name="Calibri",size=11,bold=True,color=R),PatternFill(start_color=LR,end_color=LR,fill_type="solid"),CT,MF)
    # Net Profit
    npr=29;ws.cell(row=npr,column=1,value="NET PROFIT");sc(ws.cell(row=npr,column=1),Font(name="Calibri",size=12,bold=True,color=G),LGF,LT)
    for c in range(2,15):ws.cell(row=npr,column=c).value=f"={get_column_letter(c)}14-{get_column_letter(c)}27";sc(ws.cell(row=npr,column=c),Font(name="Calibri",size=12,bold=True,color=G),LGF,CT,MF)
    # Profit Margin
    pmr=30;ws.cell(row=pmr,column=1,value="PROFIT MARGIN");sc(ws.cell(row=pmr,column=1),Font(name="Calibri",size=11,bold=True,color=G),LGF,LT)
    for c in range(2,15):ws.cell(row=pmr,column=c).value=f"=IF({get_column_letter(c)}8>0,{get_column_letter(c)}29/{get_column_letter(c)}8,0)";sc(ws.cell(row=pmr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,PF)
    ws.conditional_formatting.add(f"B29:N29",CellIsRule(operator="lessThan",formula=["0"],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
    bar=BarChart();bar.type="col";bar.title="Monthly Revenue vs Expenses";bar.style=10
    cats=Reference(ws,min_col=2,max_col=13,min_row=3)
    d1=Reference(ws,min_col=2,max_col=13,min_row=8)
    d2=Reference(ws,min_col=2,max_col=13,min_row=27)
    bar.add_data(d1,from_rows=True,titles_from_data=False);bar.add_data(d2,from_rows=True,titles_from_data=False)
    bar.set_categories(cats)
    if len(bar.series)>=2:bar.series[0].title=openpyxl.chart.series.SeriesLabel(v="Revenue");bar.series[1].title=openpyxl.chart.series.SeriesLabel(v="Expenses")
    bar.width=24;bar.height=14;ws.add_chart(bar,"A33")

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,9):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"BUSINESS DASHBOARD",8)
    cards=[("YTD Revenue","='Monthly P&L'!N8"),("YTD Expenses","='Monthly P&L'!N27"),("YTD Net Profit","='Monthly P&L'!N29"),("Profit Margin","='Monthly P&L'!N30")]
    for i,(label,formula) in enumerate(cards):
        col=i*2+1
        ws.cell(row=3,column=col,value=label);sc(ws.cell(row=3,column=col),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=3,column=col+1);sc(ws.cell(row=3,column=col+1),fill=GF)
        fmt=PF if i==3 else MF
        ws.cell(row=4,column=col,value=formula);sc(ws.cell(row=4,column=col),Font(name="Calibri",size=16,bold=True,color=D),CF,CT,fmt)
        sc(ws.cell(row=4,column=col+1),fill=CF)

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR P&L TEMPLATE",2)
    items=[("Getting Started",["1. Go to 'Monthly P&L' and update revenue/expense figures monthly","2. Dashboard will automatically show your YTD performance","3. Review profit margins to understand business health"]),
           ("Monthly Routine",["- Enter all revenue by category","- Enter all expenses by category","- Review net profit and margins","- Compare to previous months for trends"]),
           ("Tips",["- Track expenses consistently for accurate tax reporting","- Green cells = formulas, don't edit them","- Use this data for quarterly tax estimates","- Make a copy before each new year"]),
           ("Need Help?",["Message us on Etsy — happy to help!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_monthly_pl(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Monthly P&L","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Small_Business_PL_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out

if __name__=="__main__":generate()
