import json,textwrap
from graphviz import Digraph
def vis(plan):
    gr=Digraph("Plan",format="svg")
    gr.attr(rankdir="TB")
    gr.attr("node",style="filled",fontname="Helvetica",fontsize="10")
    seen={}
    cnt=[0]
    def get_id():
        cnt[0]+=1
        return "n"+str(cnt[0])
    def fmt(txt,w=32):
        return "\n".join(textwrap.fill(x,w) for x in txt.split("\n"))
    def cond(x):
        if isinstance(x,dict):
            if "table" in x and "attr" in x:
                return x["table"]+"."+x["attr"]
            if x.get("type")=="int":
                return str(x.get("value"))
            if "left" in x and "right" in x:
                return "("+cond(x["left"])+" "+x["type"]+" "+cond(x["right"])+")"
        return str(x)
    def build(node,tag=None):
        if not isinstance(node,dict):
            return None
        if node.get("type")=="expr_ref":
            rid=node["id"]
            if rid in seen:
                return seen[rid]
            if rid not in plan["common_subexpressions"]:
                return None
            actual=plan["common_subexpressions"][rid]
            nid=build(actual,rid)
            seen[rid]=nid
            return nid
        cur=get_id()
        tp=node.get("type","unknown")
        lbl=tag if tag else tp
        shp="box"
        col="#ECF0F1"
        if tp=="project":
            cols=", ".join(i["table"]+"."+i["attr"] for i in node["columns"])
            lbl="PROJ\n["+cols+"]"
            col="#ABEBC6"
            gr.node(cur,fmt(lbl),shape="box",fillcolor=col)
            ch=build(node["input"])
            if ch:gr.edge(cur,ch)
        elif tp=="select":
            c=cond(node["condition"])
            lbl="SEL\n("+c+")"
            col="#F5B7B1"
            gr.node(cur,fmt(lbl),shape="ellipse",fillcolor=col)
            ch=build(node["input"])
            if ch:gr.edge(cur,ch)
        elif tp=="join":
            c=cond(node["condition"])
            lbl="JOIN\n("+c+")"
            col="#AED6F1"
            gr.node(cur,fmt(lbl),shape="diamond",fillcolor=col)
            l=build(node["left"]);r=build(node["right"])
            if l:gr.edge(cur,l)
            if r:gr.edge(cur,r)
        elif tp=="base_relation":
            t=", ".join(x["name"] for x in node["tables"])
            lbl="REL\n["+t+"]"
            col="#F9E79F"
            gr.node(cur,fmt(lbl),shape="oval",fillcolor=col)
        elif tp=="subquery":
            lbl="SUBQ\n["+node["alias"]+"]"
            col="#D7BDE2"
            gr.node(cur,fmt(lbl),shape="parallelogram",fillcolor=col)
            ch=build(node["query"])
            if ch:gr.edge(cur,ch)
        else:
            gr.node(cur,fmt(lbl),shape=shp,fillcolor=col)
        return cur
    build(plan["query"])
    path=gr.render("query_plan",cleanup=True)
    with open(path,"r") as f:return f.read()