"""
SheetCraft AI — Product 03: Freelancer Income Tracker
Agent: 小傑
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os

G="2D5F2D";C="F5F0E8";GO="D4A574";D="1A1A1A";W="FFFFFF";LG="E8F0E8";R="CC4444";LR="FFE0E0"
GF=PatternFill(start_color=G,end_color=G,fill_type="solid")
CF=PatternFill(start_color=C,end_color=C,fill_type="solid")
WF=PatternFill(start_color=W,end_color=W,fill_type="solid")
LGF=PatternFill(start_color=LG,end_color=LG,fill_type="solid")
GOF=PatternFill(start_color=GO,end_color=GO,fill_type="solid")
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
        cell=ws.cell(row=row,column=i,value=h)
        sc(cell,Font(name="Calibri",size=11,bold=True,color=W),GF,CT)

def create_clients(wb):
    ws=wb.create_sheet("Clients")
    cols=["Client Name","Contact Person","Email","Rate Type","Rate ($)","Status","Total Billed","Notes"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"CLIENT DIRECTORY",len(cols))
    hdr(ws,3,cols)
    clients=[
        ("Acme Corp","John Smith","john@acme.com","Project",2500,"Active",7500,"Web redesign"),
        ("TechStart Inc","Sarah Lee","sarah@techstart.com","Hourly",85,"Active",5100,"Ongoing dev"),
        ("Green Media","Mike Chen","mike@greenmedia.com","Project",1800,"Active",3600,"Social media"),
        ("BlueSky LLC","Emma Davis","emma@bluesky.com","Hourly",75,"Active",4500,"Consulting"),
        ("FastFood Co","Tom Wilson","tom@fastfood.com","Project",3000,"Completed",3000,"Menu redesign"),
    ]
    for i,(name,contact,email,rtype,rate,status,billed,notes) in enumerate(clients):
        r=4+i;fill=CF if i%2==0 else WF
        vals=[name,contact,email,rtype,rate,status,billed,notes]
        for c,v in enumerate(vals,1):
            ws.cell(row=r,column=c,value=v)
            fmt=MF if c in(5,7) else None
            sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,fmt)
    return len(clients)

def create_projects(wb):
    ws=wb.create_sheet("Projects")
    cols=["Project","Client","Start Date","End Date","Hours","Rate","Total","Status","Invoice #"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=16
    title_row(ws,1,"PROJECT LOG",len(cols))
    hdr(ws,3,cols)
    projects=[
        ("Website Redesign v1","Acme Corp","2026-01-05","2026-01-25",0,2500,2500,"Paid","INV-001"),
        ("Website Redesign v2","Acme Corp","2026-02-01","2026-02-20",0,2500,2500,"Paid","INV-004"),
        ("App Development","TechStart Inc","2026-01-10","2026-02-28",60,85,5100,"Paid","INV-002"),
        ("Social Campaign Q1","Green Media","2026-01-15","2026-02-15",0,1800,1800,"Paid","INV-003"),
        ("Social Campaign Q2","Green Media","2026-03-01","2026-03-31",0,1800,1800,"Invoiced","INV-006"),
        ("Strategy Consult","BlueSky LLC","2026-01-20","2026-03-20",60,75,4500,"Invoiced","INV-005"),
        ("Menu Design","FastFood Co","2026-02-10","2026-03-10",0,3000,3000,"Paid","INV-007"),
        ("Website Redesign v3","Acme Corp","2026-03-15","",0,2500,2500,"Pending",""),
    ]
    for i,(proj,client,start,end,hrs,rate,total,status,inv) in enumerate(projects):
        r=4+i;fill=CF if i%2==0 else WF
        vals=[proj,client,start,end,hrs,rate,total,status,inv]
        for c,v in enumerate(vals,1):
            ws.cell(row=r,column=c,value=v)
            fmt=MF if c in(6,7) else None
            sc(ws.cell(row=r,column=c),NF,fill,CT if c>1 else LT,fmt)
    lr=4+len(projects)-1
    ws.conditional_formatting.add(f"H4:H{lr}",CellIsRule(operator="equal",formula=['"Paid"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"H4:H{lr}",CellIsRule(operator="equal",formula=['"Pending"'],fill=PatternFill(start_color="FFF3CD",end_color="FFF3CD",fill_type="solid"),font=Font(color="856404")))
    tr=lr+1
    ws.cell(row=tr,column=1,value="TOTAL")
    ws.cell(row=tr,column=7).value=f"=SUM(G4:G{lr})"
    for c in range(1,10):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c==7 else None)
    return len(projects)

def create_invoices(wb):
    ws=wb.create_sheet("Invoices")
    cols=["Invoice #","Client","Amount","Date Sent","Due Date","Date Paid","Status"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"INVOICE TRACKER",len(cols))
    hdr(ws,3,cols)
    invoices=[
        ("INV-001","Acme Corp",2500,"2026-01-26","2026-02-25","2026-02-10","Paid"),
        ("INV-002","TechStart Inc",5100,"2026-03-01","2026-03-31","2026-03-15","Paid"),
        ("INV-003","Green Media",1800,"2026-02-16","2026-03-16","2026-03-01","Paid"),
        ("INV-004","Acme Corp",2500,"2026-02-21","2026-03-21","2026-03-10","Paid"),
        ("INV-005","BlueSky LLC",4500,"2026-03-21","2026-04-20","","Sent"),
        ("INV-006","Green Media",1800,"2026-04-01","2026-05-01","","Sent"),
        ("INV-007","FastFood Co",3000,"2026-03-11","2026-04-10","2026-03-28","Paid"),
    ]
    for i,(inv,client,amt,sent,due,paid,status) in enumerate(invoices):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([inv,client,amt,sent,due,paid,status],1):
            ws.cell(row=r,column=c,value=v)
            sc(ws.cell(row=r,column=c),NF,fill,CT,MF if c==3 else None)
    lr=4+len(invoices)-1
    ws.conditional_formatting.add(f"G4:G{lr}",CellIsRule(operator="equal",formula=['"Paid"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"G4:G{lr}",CellIsRule(operator="equal",formula=['"Overdue"'],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
    ws.conditional_formatting.add(f"G4:G{lr}",CellIsRule(operator="equal",formula=['"Sent"'],fill=PatternFill(start_color="FFF3CD",end_color="FFF3CD",fill_type="solid"),font=Font(color="856404")))
    tr=lr+1
    ws.cell(row=tr,column=1,value="TOTAL")
    ws.cell(row=tr,column=3).value=f"=SUM(C4:C{lr})"
    for c in range(1,8):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c==3 else None)

def create_tax(wb):
    ws=wb.create_sheet("Tax Estimator")
    ws.column_dimensions["A"].width=22;ws.column_dimensions["B"].width=18;ws.column_dimensions["C"].width=18;ws.column_dimensions["D"].width=18;ws.column_dimensions["E"].width=18
    title_row(ws,1,"QUARTERLY TAX ESTIMATOR",5)
    ws.cell(row=3,column=1,value="Estimated Tax Rate:");sc(ws.cell(row=3,column=1),Font(name="Calibri",size=11,bold=True,color=G),CF,LT)
    ws.cell(row=3,column=2,value=0.25);sc(ws.cell(row=3,column=2),Font(name="Calibri",size=14,bold=True,color=D),CF,CT,PF)
    hdr(ws,5,["Quarter","Gross Income","Estimated Tax","Due Date","Status"])
    quarters=[("Q1 (Jan-Mar)",23700,"2026-04-15","Upcoming"),("Q2 (Apr-Jun)",0,"2026-06-15","Pending"),("Q3 (Jul-Sep)",0,"2026-09-15","Pending"),("Q4 (Oct-Dec)",0,"2027-01-15","Pending")]
    for i,(q,income,due,status) in enumerate(quarters):
        r=6+i;fill=CF if i%2==0 else WF
        ws.cell(row=r,column=1,value=q);ws.cell(row=r,column=2,value=income)
        ws.cell(row=r,column=3).value=f"=B{r}*$B$3"
        ws.cell(row=r,column=4,value=due);ws.cell(row=r,column=5,value=status)
        for c in range(1,6):sc(ws.cell(row=r,column=c),NF,fill,CT,MF if c in(2,3) else None)
    tr=10
    ws.cell(row=tr,column=1,value="ANNUAL TOTAL")
    ws.cell(row=tr,column=2).value="=SUM(B6:B9)";ws.cell(row=tr,column=3).value="=SUM(C6:C9)"
    for c in range(1,6):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c in(2,3) else None)

def create_monthly_report(wb):
    ws=wb.create_sheet("Monthly Report")
    cols=["Month","Revenue","Business Expenses","Net Profit","Tax Set-Aside","Take-Home"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"MONTHLY INCOME REPORT",len(cols))
    hdr(ws,3,cols)
    data=[("January",4300,350),("February",6800,420),("March",12600,580),("April",0,200),("May",0,200),("June",0,200),("July",0,200),("August",0,200),("September",0,200),("October",0,200),("November",0,200),("December",0,200)]
    for i,(month,rev,exp) in enumerate(data):
        r=4+i;fill=CF if i%2==0 else WF
        ws.cell(row=r,column=1,value=month);ws.cell(row=r,column=2,value=rev);ws.cell(row=r,column=3,value=exp)
        ws.cell(row=r,column=4).value=f"=B{r}-C{r}"
        ws.cell(row=r,column=5).value=f"=D{r}*'Tax Estimator'!$B$3"
        ws.cell(row=r,column=6).value=f"=D{r}-E{r}"
        for c in range(1,7):sc(ws.cell(row=r,column=c),NF,fill,CT,MF if c>1 else None)
    tr=16
    ws.cell(row=tr,column=1,value="TOTAL")
    for c in range(2,7):ws.cell(row=tr,column=c).value=f"=SUM({get_column_letter(c)}4:{get_column_letter(c)}15)"
    for c in range(1,7):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c>1 else None)
    bar=BarChart();bar.type="col";bar.title="Monthly Revenue & Expenses";bar.style=10
    cats=Reference(ws,min_col=1,min_row=4,max_row=15)
    d1=Reference(ws,min_col=2,min_row=3,max_row=15);d2=Reference(ws,min_col=3,min_row=3,max_row=15)
    bar.add_data(d1,titles_from_data=True);bar.add_data(d2,titles_from_data=True)
    bar.set_categories(cats);bar.width=22;bar.height=12
    ws.add_chart(bar,"A19")

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,9):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"FREELANCER INCOME DASHBOARD",8)
    cards=[("YTD Revenue","='Monthly Report'!B16"),("YTD Expenses","='Monthly Report'!C16"),("YTD Net Profit","='Monthly Report'!D16"),("Total Clients","5"),("Avg Project Value","='Monthly Report'!B16/8"),("Tax Set-Aside","='Monthly Report'!E16")]
    r=3
    for i,(label,formula) in enumerate(cards):
        col=(i%3)*2+2
        row=r if i<3 else r+2
        ws.cell(row=row,column=col,value=label);sc(ws.cell(row=row,column=col),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=row+1,column=col,value=formula);sc(ws.cell(row=row+1,column=col),Font(name="Calibri",size=16,bold=True,color=D),CF,CT,MF)
    pie=PieChart();pie.title="Revenue by Client";pie.style=10
    # Reference Clients sheet total billed
    ws.cell(row=9,column=2,value="Acme Corp");ws.cell(row=9,column=3,value=7500)
    ws.cell(row=10,column=2,value="TechStart Inc");ws.cell(row=10,column=3,value=5100)
    ws.cell(row=11,column=2,value="Green Media");ws.cell(row=11,column=3,value=3600)
    ws.cell(row=12,column=2,value="BlueSky LLC");ws.cell(row=12,column=3,value=4500)
    ws.cell(row=13,column=2,value="FastFood Co");ws.cell(row=13,column=3,value=3000)
    for r2 in range(9,14):
        sc(ws.cell(row=r2,column=2),NF,CF,LT);sc(ws.cell(row=r2,column=3),NF,CF,CT,MF)
    cats=Reference(ws,min_col=2,min_row=9,max_row=13)
    data=Reference(ws,min_col=3,min_row=8,max_row=13)
    pie.add_data(data,titles_from_data=True);pie.set_categories(cats);pie.width=16;pie.height=10
    ws.add_chart(pie,"E8")

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR FREELANCER INCOME TRACKER",2)
    items=[("Getting Started",["1. Add your clients in the 'Clients' tab","2. Log your projects in the 'Projects' tab","3. Track invoices in the 'Invoices' tab","4. Set your tax rate in 'Tax Estimator'","5. Check Dashboard for your complete overview!"]),
           ("Monthly Routine",["- Log all new projects and update statuses","- Send invoices promptly and track in Invoices tab","- Update Monthly Report with actual revenue","- Review tax set-aside quarterly"]),
           ("Tips",["- Keep invoice numbers sequential (INV-001, INV-002...)","- Update project status as soon as payment is received","- Review Dashboard weekly to track cash flow","- Set aside tax money in a separate account"]),
           ("Need Help?",["Message us on Etsy — happy to help!","Thank you for your purchase!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:
            ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_clients(wb);create_projects(wb);create_invoices(wb);create_tax(wb);create_monthly_report(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Clients","Projects","Invoices","Tax Estimator","Monthly Report","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Freelancer_Income_Tracker_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out

if __name__=="__main__":generate()
