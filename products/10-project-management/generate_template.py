"""SheetCraft AI — Product 10: Project Management Board. Agent: 阿管"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, Reference
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
def create_projects(wb):
    ws=wb.create_sheet("Projects")
    cols=["Project Name","Description","Owner","Start Date","Due Date","Status","Priority","Budget","Spent","% Complete"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"PROJECT OVERVIEW",len(cols));hdr(ws,3,cols)
    projects=[("Website Redesign","Complete overhaul of company site","Sarah","2026-01-15","2026-04-30","In Progress","High",25000,12500,0.50),("Mobile App v2","Native app rebuild","Mike","2026-02-01","2026-06-30","In Progress","High",40000,8000,0.20),("CRM Integration","Connect CRM to all systems","Lisa","2026-03-01","2026-05-15","Not Started","Medium",15000,0,0)]
    for i,(name,desc,owner,start,due,status,pri,budget,spent,pct) in enumerate(projects):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([name,desc,owner,start,due,status,pri,budget,spent,pct],1):
            ws.cell(row=r,column=c,value=v);fmt=MF if c in(8,9) else(PF if c==10 else None);sc(ws.cell(row=r,column=c),NF,fill,CT if c in(6,7,10) else LT,fmt)
    lr=4+len(projects)-1
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"Completed"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="equal",formula=['"In Progress"'],fill=PatternFill(start_color="D4E6F1",end_color="D4E6F1",fill_type="solid"),font=Font(color="1B4F72")))
    ws.conditional_formatting.add(f"G4:G{lr}",CellIsRule(operator="equal",formula=['"High"'],fill=PatternFill(start_color="FADBD8",end_color="FADBD8",fill_type="solid"),font=Font(color=R,bold=True)))
def create_tasks(wb):
    ws=wb.create_sheet("Task Board")
    cols=["Task","Project","Assignee","Status","Priority","Due Date","Est Hours","Actual Hours","Notes"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"TASK BOARD",len(cols));hdr(ws,3,cols)
    tasks=[("Design mockups","Website Redesign","Sarah","Done","High","2026-02-01",16,18,"Approved"),("Frontend build","Website Redesign","Tom","In Progress","High","2026-03-15",40,20,"React"),("Backend API","Website Redesign","Mike","In Progress","High","2026-03-20",32,12,"REST"),("Content migration","Website Redesign","Lisa","To Do","Medium","2026-04-01",20,0,"500+ pages"),("UI/UX research","Mobile App v2","Sarah","Done","High","2026-02-15",24,22,"Done"),("App wireframes","Mobile App v2","Sarah","In Progress","High","2026-03-01",20,15,"80%"),("iOS development","Mobile App v2","Tom","To Do","High","2026-04-15",80,0,"Swift"),("Android dev","Mobile App v2","Mike","To Do","High","2026-04-15",80,0,"Kotlin"),("API integration","Mobile App v2","Mike","To Do","Medium","2026-05-01",40,0,"REST+WS"),("Requirements doc","CRM Integration","Lisa","Review","High","2026-03-10",8,6,"In review"),("Vendor evaluation","CRM Integration","Lisa","To Do","Medium","2026-03-20",16,0,"3 vendors"),("Data mapping","CRM Integration","Tom","To Do","Medium","2026-04-01",24,0,"Fields")]
    for i,(task,proj,assignee,status,pri,due,est,act,notes) in enumerate(tasks):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([task,proj,assignee,status,pri,due,est,act,notes],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,CT if c in(4,5,7,8) else LT)
    lr=4+len(tasks)-1
    ws.conditional_formatting.add(f"D4:D{lr}",CellIsRule(operator="equal",formula=['"Done"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"D4:D{lr}",CellIsRule(operator="equal",formula=['"In Progress"'],fill=PatternFill(start_color="D4E6F1",end_color="D4E6F1",fill_type="solid"),font=Font(color="1B4F72")))
    ws.conditional_formatting.add(f"D4:D{lr}",CellIsRule(operator="equal",formula=['"Review"'],fill=PatternFill(start_color="FFF3CD",end_color="FFF3CD",fill_type="solid"),font=Font(color="856404")))
    tr=lr+1;ws.cell(row=tr,column=1,value="TOTALS");ws.cell(row=tr,column=7).value=f"=SUM(G4:G{lr})";ws.cell(row=tr,column=8).value=f"=SUM(H4:H{lr})"
    for c in range(1,10):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT)
def create_meetings(wb):
    ws=wb.create_sheet("Meeting Notes")
    cols=["Date","Project","Attendees","Agenda","Decisions","Action Items","Owner","Due Date"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"MEETING NOTES",len(cols));hdr(ws,3,cols)
    meetings=[("2026-01-20","Website Redesign","Sarah, Tom, Mike","Kickoff","Approved timeline","Create design system","Sarah","2026-02-01"),("2026-02-05","Mobile App v2","Sarah, Tom, Mike","UX research","Go native","Start wireframes","Sarah","2026-02-15"),("2026-03-01","CRM Integration","Lisa, Tom","Requirements","Salesforce primary","Draft requirements","Lisa","2026-03-10")]
    for i,(date,proj,att,agenda,decisions,actions,owner,due) in enumerate(meetings):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,proj,att,agenda,decisions,actions,owner,due],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,LT)
    for i in range(len(meetings),20):
        r=4+i;fill=CF if i%2==0 else WF
        for c in range(1,9):sc(ws.cell(row=r,column=c),NF,fill,LT)
def create_resources(wb):
    ws=wb.create_sheet("Resources")
    cols=["Team Member","Role","Projects","Allocated Hours","Available Hours","Utilization"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"RESOURCE TRACKER",len(cols));hdr(ws,3,cols)
    team=[("Sarah","Design Lead","Website, Mobile App",36,40),("Tom","Frontend Dev","Website, Mobile App, CRM",38,40),("Mike","Backend Dev","Website, Mobile App",32,40),("Lisa","PM","CRM, Website",24,40)]
    for i,(name,role,projs,alloc,avail) in enumerate(team):
        r=4+i;fill=CF if i%2==0 else WF
        ws.cell(row=r,column=1,value=name);ws.cell(row=r,column=2,value=role);ws.cell(row=r,column=3,value=projs);ws.cell(row=r,column=4,value=alloc);ws.cell(row=r,column=5,value=avail)
        ws.cell(row=r,column=6).value=f"=IF(E{r}>0,D{r}/E{r},0)"
        for c in range(1,7):sc(ws.cell(row=r,column=c),NF,fill,CT if c in(4,5,6) else LT,PF if c==6 else None)
    lr=4+len(team)-1
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="greaterThan",formula=["0.9"],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
    ws.conditional_formatting.add(f"F4:F{lr}",CellIsRule(operator="lessThanOrEqual",formula=["0.7"],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G)))
def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,8):ws.column_dimensions[get_column_letter(c)].width=18
    title_row(ws,1,"PROJECT MANAGEMENT DASHBOARD",7)
    cards=[("Total Projects","3"),("In Progress","2"),("Completion Rate","=2/12"),("Overdue Tasks","0")]
    for i,(label,val) in enumerate(cards):
        col=i+2;ws.cell(row=3,column=col,value=label);sc(ws.cell(row=3,column=col),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=4,column=col,value=val);sc(ws.cell(row=4,column=col),Font(name="Calibri",size=16,bold=True,color=D),CF,CT,PF if i==2 else '#,##0')
    ws.cell(row=7,column=2,value="Done");ws.cell(row=7,column=3,value=3)
    ws.cell(row=8,column=2,value="In Progress");ws.cell(row=8,column=3,value=3)
    ws.cell(row=9,column=2,value="Review");ws.cell(row=9,column=3,value=1)
    ws.cell(row=10,column=2,value="To Do");ws.cell(row=10,column=3,value=5)
    for r in range(7,11):sc(ws.cell(row=r,column=2),NF,CF,LT);sc(ws.cell(row=r,column=3),NF,CF,CT)
    pie=PieChart();pie.title="Tasks by Status";pie.style=10
    cats=Reference(ws,min_col=2,min_row=7,max_row=10);data=Reference(ws,min_col=3,min_row=6,max_row=10)
    pie.add_data(data,titles_from_data=True);pie.set_categories(cats);pie.width=14;pie.height=10
    ws.add_chart(pie,"B12")
def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR PROJECT MANAGEMENT BOARD",2)
    items=[("Getting Started",["1. Add projects to Projects tab","2. Break work into tasks in Task Board","3. Track team in Resources","4. Log meetings in Meeting Notes","5. Monitor on Dashboard"]),("Status Flow",["To Do -> In Progress -> Review -> Done","Update daily for accuracy"]),("Tips",["- Keep tasks 2-8 hours each","- Update % complete weekly","- Watch utilization to prevent burnout"]),("Need Help?",["Message us on Etsy!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1
def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_projects(wb);create_tasks(wb);create_meetings(wb);create_resources(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Projects","Task Board","Meeting Notes","Resources","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Project_Management_Board_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out
if __name__=="__main__":generate()
