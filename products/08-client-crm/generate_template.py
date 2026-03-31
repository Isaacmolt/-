"""SheetCraft AI — Product 08: Client CRM Tracker. Agent: 小客"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os
G="2D5F2D";C="F5F0E8";D="1A1A1A";W="FFFFFF";LG="E8F0E8";R="CC4444";LR="FFE0E0";GO="D4A574"
GF=PatternFill(start_color=G,end_color=G,fill_type="solid");CF=PatternFill(start_color=C,end_color=C,fill_type="solid")
WF=PatternFill(start_color=W,end_color=W,fill_type="solid");LGF=PatternFill(start_color=LG,end_color=LG,fill_type="solid")
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

def create_clients(wb):
    ws=wb.create_sheet("Clients")
    cols=["Client Name","Company","Email","Phone","Source","Status","Start Date","Lifetime Value","Notes"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"CLIENT DATABASE",len(cols))
    hdr(ws,3,cols)
    clients=[("Alice Johnson","TechFlow Inc","alice@techflow.com","555-1001","Referral","Active","2025-06-15",12500,"Enterprise client"),
             ("Bob Martinez","GreenLeaf Co","bob@greenleaf.com","555-1002","Website","Active","2025-08-20",8200,"Monthly retainer"),
             ("Carol Chen","DataPro LLC","carol@datapro.com","555-1003","Social Media","Active","2025-10-01",6800,"Project-based"),
             ("David Park","StartUp Hub","david@startuphub.com","555-1004","Cold Outreach","Lead","2026-01-10",0,"Initial contact made"),
             ("Emma Wilson","BrightStar","emma@brightstar.com","555-1005","Referral","Active","2025-03-05",15600,"Top client"),
             ("Frank Liu","MediaMax","frank@mediamax.com","555-1006","Website","Inactive","2025-01-20",4200,"Last project Dec 2025"),
             ("Grace Kim","EduTech","grace@edutech.com","555-1007","Social Media","Lead","2026-02-15",0,"Proposal sent"),
             ("Henry Brown","FinServe","henry@finserve.com","555-1008","Referral","Active","2025-11-01",9400,"Quarterly projects")]
    for i,(name,co,email,phone,src,status,start,ltv,notes) in enumerate(clients):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([name,co,email,phone,src,status,start,ltv,notes],1):
            ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,CT if c in(5,6,8) else LT,MF if c==8 else None)
    lr=4+len(clients)-1
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Active"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Lead"'],fill=PatternFill(start_color="FFF3CD",end_color="FFF3CD",fill_type="solid"),font=Font(color="856404")))
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Inactive"'],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R)))

def create_interactions(wb):
    ws=wb.create_sheet("Interactions")
    cols=["Date","Client","Type","Summary","Next Action","Action Date"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=22
    title_row(ws,1,"INTERACTION LOG",len(cols))
    hdr(ws,3,cols)
    logs=[("2026-01-05","Alice Johnson","Meeting","Quarterly review","Send updated proposal","2026-01-12"),
          ("2026-01-08","Bob Martinez","Email","Monthly report sent","Schedule review call","2026-01-15"),
          ("2026-01-10","David Park","Call","Initial discovery call","Send capabilities deck","2026-01-12"),
          ("2026-01-12","Emma Wilson","Meeting","Strategy session","Draft Q1 plan","2026-01-19"),
          ("2026-01-15","Carol Chen","Email","Project milestone update","Review deliverables","2026-01-20"),
          ("2026-01-18","Grace Kim","Call","Proposal walkthrough","Follow up on decision","2026-01-25"),
          ("2026-01-20","Henry Brown","Meeting","Q1 kickoff","Begin project scope","2026-01-27"),
          ("2026-01-22","Alice Johnson","Email","Proposal sent","Await response","2026-01-29"),
          ("2026-01-25","Bob Martinez","Call","Budget discussion","Revise pricing","2026-02-01"),
          ("2026-02-01","David Park","Follow-up","Decision pending","Second follow-up","2026-02-08"),
          ("2026-02-05","Emma Wilson","Meeting","Creative review","Finalize designs","2026-02-12"),
          ("2026-02-08","Carol Chen","Email","Invoice sent","Confirm payment","2026-02-15"),
          ("2026-02-10","Grace Kim","Follow-up","Still evaluating","Final follow-up","2026-02-17"),
          ("2026-02-15","Henry Brown","Call","Progress update","Send weekly report","2026-02-22"),
          ("2026-02-20","Alice Johnson","Meeting","Contract renewal","Prepare renewal docs","2026-02-27")]
    for i,(date,client,itype,summary,action,adate) in enumerate(logs):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,client,itype,summary,action,adate],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,CT if c==3 else LT)
    lr=4+len(logs)-1
    ws.conditional_formatting.add(f"C4:C{lr}",CellIsRule(operator="equal",formula=['"Meeting"'],fill=PatternFill(start_color="D4E6F1",end_color="D4E6F1",fill_type="solid"),font=Font(color="1B4F72")))
    ws.conditional_formatting.add(f"C4:C{lr}",CellIsRule(operator="equal",formula=['"Call"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G)))
    ws.conditional_formatting.add(f"C4:C{lr}",CellIsRule(operator="equal",formula=['"Email"'],fill=PatternFill(start_color="FFF3CD",end_color="FFF3CD",fill_type="solid"),font=Font(color="856404")))
    for i in range(len(logs),50):
        r=4+i;fill=CF if i%2==0 else WF
        for c in range(1,7):sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_pipeline(wb):
    ws=wb.create_sheet("Sales Pipeline")
    cols=["Deal Name","Client","Stage","Value","Probability","Expected Close","Weighted Value"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"SALES PIPELINE",len(cols))
    hdr(ws,3,cols)
    deals=[("Website Redesign","David Park","Qualified",8000,0.4,"2026-03-15"),
           ("Annual Retainer","Grace Kim","Proposal",24000,0.6,"2026-04-01"),
           ("Q2 Campaign","Alice Johnson","Negotiation",15000,0.8,"2026-03-30"),
           ("Data Migration","Carol Chen","Lead",5000,0.2,"2026-05-01"),
           ("Brand Strategy","Henry Brown","Proposal",12000,0.5,"2026-04-15")]
    for i,(deal,client,stage,val,prob,close) in enumerate(deals):
        r=4+i;fill=CF if i%2==0 else WF
        ws.cell(row=r,column=1,value=deal);ws.cell(row=r,column=2,value=client);ws.cell(row=r,column=3,value=stage)
        ws.cell(row=r,column=4,value=val);ws.cell(row=r,column=5,value=prob);ws.cell(row=r,column=6,value=close)
        ws.cell(row=r,column=7).value=f"=D{r}*E{r}"
        for c in range(1,8):sc(ws.cell(row=r,column=c),NF,fill,CT if c in(3,4,5,7) else LT,MF if c in(4,7) else(PF if c==5 else None))
    tr=4+len(deals)
    ws.cell(row=tr,column=1,value="TOTAL PIPELINE")
    ws.cell(row=tr,column=4).value=f"=SUM(D4:D{tr-1})";ws.cell(row=tr,column=7).value=f"=SUM(G4:G{tr-1})"
    for c in range(1,8):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c in(4,7) else None)
    bar=BarChart();bar.type="col";bar.title="Pipeline by Stage";bar.style=10
    cats=Reference(ws,min_col=1,min_row=4,max_row=tr-1)
    data=Reference(ws,min_col=4,min_row=3,max_row=tr-1)
    bar.add_data(data,titles_from_data=True);bar.set_categories(cats);bar.width=18;bar.height=10
    ws.add_chart(bar,f"A{tr+3}")

def create_revenue(wb):
    ws=wb.create_sheet("Revenue Log")
    cols=["Date","Client","Invoice #","Amount","Service","Status"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"REVENUE LOG",len(cols))
    hdr(ws,3,cols)
    revs=[("2025-12-15","Emma Wilson","INV-2025-12",3900,"Strategy Consulting","Paid"),
          ("2026-01-05","Alice Johnson","INV-2026-01",4200,"Web Development","Paid"),
          ("2026-01-15","Bob Martinez","INV-2026-02",2800,"Monthly Retainer","Paid"),
          ("2026-02-01","Emma Wilson","INV-2026-03",3900,"Strategy Consulting","Paid"),
          ("2026-02-05","Carol Chen","INV-2026-04",3400,"Data Analysis","Paid"),
          ("2026-02-15","Bob Martinez","INV-2026-05",2800,"Monthly Retainer","Paid"),
          ("2026-03-01","Henry Brown","INV-2026-06",4700,"Brand Consulting","Pending"),
          ("2026-03-10","Alice Johnson","INV-2026-07",4100,"Web Development","Pending"),
          ("2026-03-15","Emma Wilson","INV-2026-08",3900,"Strategy Consulting","Overdue")]
    for i,(date,client,inv,amt,svc,status) in enumerate(revs):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,client,inv,amt,svc,status],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,CT if c in(3,4,6) else LT,MF if c==4 else None)
    lr=4+len(revs)-1
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Paid"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Overdue"'],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Pending"'],fill=PatternFill(start_color="FFF3CD",end_color="FFF3CD",fill_type="solid"),font=Font(color="856404")))
    tr=lr+1
    ws.cell(row=tr,column=1,value="TOTAL");ws.cell(row=tr,column=4).value=f"=SUM(D4:D{lr})"
    for c in range(1,7):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c==4 else None)

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,8):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"CLIENT CRM DASHBOARD",7)
    cards=[("Total Clients","8"),("Active Clients","5"),("Total Revenue","='Revenue Log'!D13"),("Pipeline Value","='Sales Pipeline'!D9"),("Avg Client Value","='Revenue Log'!D13/5")]
    for i,(label,formula) in enumerate(cards):
        col=i+2
        ws.cell(row=3,column=col,value=label);sc(ws.cell(row=3,column=col),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=4,column=col,value=formula);sc(ws.cell(row=4,column=col),Font(name="Calibri",size=14,bold=True,color=D),CF,CT,MF if i>=2 else '#,##0')
    # Revenue by client pie
    ws.cell(row=7,column=2,value="Alice Johnson");ws.cell(row=7,column=3,value=8300)
    ws.cell(row=8,column=2,value="Bob Martinez");ws.cell(row=8,column=3,value=5600)
    ws.cell(row=9,column=2,value="Emma Wilson");ws.cell(row=9,column=3,value=11700)
    ws.cell(row=10,column=2,value="Carol Chen");ws.cell(row=10,column=3,value=3400)
    ws.cell(row=11,column=2,value="Henry Brown");ws.cell(row=11,column=3,value=4700)
    for r in range(7,12):sc(ws.cell(row=r,column=2),NF,CF,LT);sc(ws.cell(row=r,column=3),NF,CF,CT,MF)
    pie=PieChart();pie.title="Revenue by Client";pie.style=10
    cats=Reference(ws,min_col=2,min_row=7,max_row=11);data=Reference(ws,min_col=3,min_row=6,max_row=11)
    pie.add_data(data,titles_from_data=True);pie.set_categories(cats);pie.width=16;pie.height=10
    ws.add_chart(pie,"B13")

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR CRM TRACKER",2)
    items=[("Getting Started",["1. Add clients to the 'Clients' tab","2. Log all interactions in 'Interactions'","3. Track deals in 'Sales Pipeline'","4. Record revenue in 'Revenue Log'","5. Check Dashboard for overview!"]),
           ("Tips",["- Log every client interaction immediately","- Update pipeline stages as deals progress","- Review Dashboard weekly","- Follow up on overdue invoices promptly"]),
           ("Need Help?",["Message us on Etsy!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_clients(wb);create_interactions(wb);create_pipeline(wb);create_revenue(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Clients","Interactions","Sales Pipeline","Revenue Log","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Client_CRM_Tracker_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out
if __name__=="__main__":generate()
