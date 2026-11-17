"""Standalone statistical figures using ReportLab charts (SVG), no GUI required."""
from pathlib import Path
import math
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing,String,Rect,Line
from reportlab.graphics.charts.barcharts import VerticalBarChart,HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors

PALETTE=['#2563eb','#ea580c','#059669','#9333ea','#dc2626','#0891b2','#ca8a04','#475569']

def figure(title,subtitle='',width=1100,height=650):
    drawing=Drawing(width,height)
    drawing.add(Rect(0,0,width,height,fillColor=colors.white,strokeColor=None))
    drawing.add(String(36,height-38,title,fontName='Helvetica-Bold',fontSize=21,fillColor=colors.HexColor('#0f172a')))
    if subtitle:drawing.add(String(36,height-64,subtitle,fontSize=11,fillColor=colors.HexColor('#475569')))
    return drawing

def note(drawing,text):
    drawing.add(String(36,20,text,fontSize=9,fillColor=colors.HexColor('#475569')))

def bars(drawing,values,labels,x,y,width,height,title='',horizontal=False,series_labels=None,rotate=0):
    chart=HorizontalBarChart() if horizontal else VerticalBarChart()
    chart.x=x;chart.y=y;chart.width=width;chart.height=height
    chart.data=values if isinstance(values[0],(list,tuple)) else [list(values)]
    chart.categoryAxis.categoryNames=list(labels)
    chart.categoryAxis.labels.fontName='Helvetica';chart.categoryAxis.labels.fontSize=9
    chart.valueAxis.labels.fontSize=9;chart.valueAxis.valueMin=0
    chart.valueAxis.strokeColor=colors.HexColor('#94a3b8')
    chart.categoryAxis.strokeColor=colors.HexColor('#94a3b8')
    chart.valueAxis.gridStrokeColor=colors.HexColor('#e2e8f0');chart.valueAxis.visibleGrid=1
    chart.strokeColor=None
    for i in range(len(chart.data)):
        chart.bars[i].fillColor=colors.HexColor(PALETTE[i%len(PALETTE)])
        chart.bars[i].strokeColor=None
    if rotate:
        chart.categoryAxis.labels.angle=rotate;chart.categoryAxis.labels.boxAnchor='ne';chart.categoryAxis.labels.dy=-5
    drawing.add(chart)
    if title:drawing.add(String(x,y+height+25,title,fontName='Helvetica-Bold',fontSize=12,fillColor=colors.HexColor('#0f172a')))
    if series_labels:
        for i,label in enumerate(series_labels):
            drawing.add(Rect(x+i*190,y+height+4,10,10,fillColor=colors.HexColor(PALETTE[i]),strokeColor=None))
            drawing.add(String(x+15+i*190,y+height+5,label,fontSize=9))
    return chart

def lines(drawing,data,x,y,width,height,title='',labels=None,scatter=False):
    chart=LinePlot();chart.x=x;chart.y=y;chart.width=width;chart.height=height
    chart.data=data
    chart.xValueAxis.labels.fontSize=9;chart.yValueAxis.labels.fontSize=9
    chart.yValueAxis.visibleGrid=1;chart.yValueAxis.gridStrokeColor=colors.HexColor('#e2e8f0')
    for i in range(len(data)):
        color=colors.HexColor(PALETTE[i%len(PALETTE)])
        chart.lines[i].strokeColor=None if scatter else color
        chart.lines[i].strokeWidth=2
        marker=makeMarker('FilledCircle');marker.size=2.4 if scatter else 5;marker.fillColor=color;marker.strokeColor=None
        chart.lines[i].symbol=marker
    drawing.add(chart)
    if title:drawing.add(String(x,y+height+25,title,fontName='Helvetica-Bold',fontSize=12))
    if labels:
        for i,label in enumerate(labels):
            drawing.add(String(x+i*180,y+height+5,label,fontSize=10,fillColor=colors.HexColor(PALETTE[i%len(PALETTE)])))
    return chart

def save(drawing,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    renderSVG.drawToFile(drawing,str(path))
