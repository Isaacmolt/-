"""SheetCraft AI — Product 07: Inventory Manager. Agent: 阿庫"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
import os
G="2D5F2D";C="F5F0E8";D="1A1A1A";W="FFFFFF";LG="E8F0E8";R="CC4444";LR="FFE0E0"
GF=PatternFill(start_color=G,end_color=G,fill_type="solid");CF=PatternFill(start_color=C,end_color=C,fill_type="solid")
WF=PatternFill(start_color=W,end_color=W,fill_type="solid");LGF=PatternFill(start_color=LG,end_color=LG,fill_type="solid")
NF=Font(name="Calibri",size=11,color=D)
TB=Border(left=Side(style="thin",color="CCCCCC"),right=Side(style="thin",color="CCCCCC"),top=Side(style="thin",color="CCCCCC"),bottom=Side(style="thin",color="CCCCCC"))
CT=Alignment(horizontal="center",vertical="center");LT=Alignment(horizontal="left",vertical="center");WR=Alignment(horizontal="left",vertical="top",wrap_text=True)
MF='#,##0.00'
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

def create_inventory(wb):
    ws=wb.create_sheet("Inventory")
    cols=["SKU","Product Name","Category","Qty on Hand","Reorder Level","Unit Cost","Total Value","Supplier","Location","Last Updated"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=16
    title_row(ws,1,"INVENTORY LIST",len(cols))
    hdr(ws,3,cols)
    items=[
        ("SKU-001","Wireless Mouse","Electronics",45,20,12.99,"TechSupply Co","Shelf A1","2026-03-15"),
        ("SKU-002","USB-C Cable","Electronics",120,50,4.99,"TechSupply Co","Shelf A2","2026-03-20"),
        ("SKU-003","Notebook A5","Office",200,100,2.50,"PaperWorld","Shelf B1","2026-03-18"),
        ("SKU-004","Desk Lamp","Office",15,10,28.99,"HomeGoods","Shelf B2","2026-03-10"),
        ("SKU-005","Phone Case","Accessories",80,30,8.99,"CaseMaker","Shelf C1","2026-03-22"),
        ("SKU-006","Webcam HD","Electronics",8,15,45.99,"TechSupply Co","Shelf A3","2026-03-01"),
        ("SKU-007","Sticky Notes","Office",300,150,1.99,"PaperWorld","Shelf B3","2026-03-25"),
        ("SKU-008","Bluetooth Speaker","Electronics",22,20,35.99,"TechSupply Co","Shelf A4","2026-03-12"),
        ("SKU-009","Pen Set","Office",150,75,6.99,"PaperWorld","Shelf B4","2026-03-20"),
        ("SKU-010","Screen Protector","Accessories",60,25,3.99,"CaseMaker","Shelf C2","2026-03-15"),
        ("SKU-011","Keyboard","Electronics",18,10,49.99,"TechSupply Co","Shelf A5","2026-03-08"),
        ("SKU-012","Clipboard","Office",90,40,4.50,"PaperWorld","Shelf B5","2026-03-22"),
        ("SKU-013","Phone Stand","Accessories",35,15,11.99,"CaseMaker","Shelf C3","2026-03-18"),
        ("SKU-014","HDMI Cable","Electronics",5,20,9.99,"TechSupply Co","Shelf A6","2026-02-28"),
        ("SKU-015","Whiteboard Marker","Office",250,100,1.50,"PaperWorld","Shelf B6","2026-03-25"),
    ]
    for i,(sku,name,cat,qty,reorder,cost,supplier,loc,updated) in enumerate(items):
        r=4+i;fill=CF if i%2==0 else WF
        ws.cell(row=r,column=1,value=sku);ws.cell(row=r,column=2,value=name);ws.cell(row=r,column=3,value=cat)
        ws.cell(row=r,column=4,value=qty);ws.cell(row=r,column=5,value=reorder);ws.cell(row=r,column=6,value=cost)
        ws.cell(row=r,column=7).value=f"=D{r}*F{r}"
        ws.cell(row=r,column=8,value=supplier);ws.cell(row=r,column=9,value=loc);ws.cell(row=r,column=10,value=updated)
        for c in range(1,11):sc(ws.cell(row=r,column=c),NF,fill,CT if c not in(2,8) else LT,MF if c in(6,7) else None)
    lr=4+len(items)-1
    ws.conditional_formatting.add(f"D4:D{lr}",CellIsRule(operator="lessThanOrEqual",formula=["E4"],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R,bold=True)))
    tr=lr+1
    ws.cell(row=tr,column=1,value="TOTALS");ws.cell(row=tr,column=4).value=f"=SUM(D4:D{lr})";ws.cell(row=tr,column=7).value=f"=SUM(G4:G{lr})"
    for c in range(1,11):sc(ws.cell(row=tr,column=c),Font(name="Calibri",size=11,bold=True,color=G),LGF,CT,MF if c==7 else None)
    return len(items)

def create_movements(wb):
    ws=wb.create_sheet("Stock Movement")
    cols=["Date","SKU","Product","Type","Quantity","Reference","Notes"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=18
    title_row(ws,1,"STOCK MOVEMENTS",len(cols))
    hdr(ws,3,cols)
    moves=[("2026-03-01","SKU-001","Wireless Mouse","IN",50,"PO-001","Restocking"),("2026-03-05","SKU-001","Wireless Mouse","OUT",5,"ORD-101","Customer order"),("2026-03-08","SKU-006","Webcam HD","OUT",7,"ORD-102","Bulk order"),("2026-03-10","SKU-014","HDMI Cable","OUT",15,"ORD-103",""),("2026-03-12","SKU-003","Notebook A5","IN",100,"PO-002","Monthly restock"),("2026-03-15","SKU-002","USB-C Cable","OUT",30,"ORD-104",""),("2026-03-18","SKU-008","Bluetooth Speaker","IN",20,"PO-003","New batch"),("2026-03-20","SKU-005","Phone Case","OUT",10,"ORD-105",""),]
    for i,(date,sku,prod,mtype,qty,ref,notes) in enumerate(moves):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([date,sku,prod,mtype,qty,ref,notes],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,CT if c not in(3,7) else LT)
    lr=4+len(moves)-1
    ws.conditional_formatting.add(f"D4:D{lr}",CellIsRule(operator="equal",formula=['"IN"'],fill=PatternFill(start_color=LG,end_color=LG,fill_type="solid"),font=Font(color=G,bold=True)))
    ws.conditional_formatting.add(f"D4:D{lr}",CellIsRule(operator="equal",formula=['"OUT"'],fill=PatternFill(start_color=LR,end_color=LR,fill_type="solid"),font=Font(color=R)))
    for i in range(len(moves),50):
        r=4+i;fill=CF if i%2==0 else WF
        for c in range(1,8):sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_suppliers(wb):
    ws=wb.create_sheet("Suppliers")
    cols=["Supplier Name","Contact","Email","Phone","Payment Terms","Notes"]
    for i in range(len(cols)):ws.column_dimensions[get_column_letter(i+1)].width=20
    title_row(ws,1,"SUPPLIER DIRECTORY",len(cols))
    hdr(ws,3,cols)
    suppliers=[("TechSupply Co","James Brown","james@techsupply.com","555-0101","Net 30","Primary electronics supplier"),("PaperWorld","Lisa Wang","lisa@paperworld.com","555-0202","Net 15","Office supplies"),("CaseMaker","David Kim","david@casemaker.com","555-0303","Net 30","Phone accessories")]
    for i,(name,contact,email,phone,terms,notes) in enumerate(suppliers):
        r=4+i;fill=CF if i%2==0 else WF
        for c,v in enumerate([name,contact,email,phone,terms,notes],1):ws.cell(row=r,column=c,value=v);sc(ws.cell(row=r,column=c),NF,fill,LT)

def create_dashboard(wb):
    ws=wb.create_sheet("Dashboard")
    for c in range(1,7):ws.column_dimensions[get_column_letter(c)].width=20
    title_row(ws,1,"INVENTORY DASHBOARD",6)
    cards=[("Total SKUs","=COUNTA(Inventory!A4:A18)"),("Total Units","=Inventory!D19"),("Total Value","=Inventory!G19"),("Low Stock Items","=COUNTIF(Inventory!D4:D18,\"<=\"&Inventory!E4)")]
    for i,(label,formula) in enumerate(cards):
        col=i+2;r=3
        ws.cell(row=r,column=col,value=label);sc(ws.cell(row=r,column=col),Font(name="Calibri",size=10,bold=True,color=W),GF,CT)
        ws.cell(row=r+1,column=col,value=formula);sc(ws.cell(row=r+1,column=col),Font(name="Calibri",size=16,bold=True,color=D),CF,CT,MF if i==2 else '#,##0')
    # Category breakdown
    ws.cell(row=7,column=2,value="Electronics");ws.cell(row=7,column=3,value=6)
    ws.cell(row=8,column=2,value="Office");ws.cell(row=8,column=3,value=6)
    ws.cell(row=9,column=2,value="Accessories");ws.cell(row=9,column=3,value=3)
    for r in range(7,10):sc(ws.cell(row=r,column=2),NF,CF,LT);sc(ws.cell(row=r,column=3),NF,CF,CT)
    pie=PieChart();pie.title="Inventory by Category";pie.style=10
    cats=Reference(ws,min_col=2,min_row=7,max_row=9);data=Reference(ws,min_col=3,min_row=6,max_row=9)
    pie.add_data(data,titles_from_data=True);pie.set_categories(cats);pie.width=14;pie.height=10
    ws.add_chart(pie,"B11")

def create_instructions(wb):
    ws=wb.create_sheet("Instructions")
    ws.column_dimensions["A"].width=5;ws.column_dimensions["B"].width=80
    title_row(ws,1,"HOW TO USE YOUR INVENTORY MANAGER",2)
    items=[("Getting Started",["1. Add all products to the 'Inventory' tab","2. Set reorder levels for automatic low-stock alerts","3. Log stock movements (IN/OUT) in 'Stock Movement'","4. Add supplier info in 'Suppliers'"]),
           ("Daily Use",["- Log every stock movement immediately","- Items below reorder level highlight in RED","- Check Dashboard for quick overview"]),
           ("Need Help?",["Message us on Etsy!"])]
    row=3
    for title,lines in items:
        ws.cell(row=row,column=2,value=title);sc(ws.cell(row=row,column=2),Font(name="Calibri",size=13,bold=True,color=G),LGF,LT);row+=1
        for line in lines:ws.cell(row=row,column=2,value=line);sc(ws.cell(row=row,column=2),NF,WF,WR);ws.row_dimensions[row].height=22;row+=1
        row+=1

def generate():
    wb=openpyxl.Workbook();wb.remove(wb.active)
    create_inventory(wb);create_movements(wb);create_suppliers(wb);create_dashboard(wb);create_instructions(wb)
    order=["Dashboard","Inventory","Stock Movement","Suppliers","Instructions"]
    for i,name in enumerate(order):wb.move_sheet(name,offset=i-wb.sheetnames.index(name))
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"Inventory_Manager_SheetCraft.xlsx")
    wb.save(out);print(f"Generated: {out}");return out
if __name__=="__main__":generate()
