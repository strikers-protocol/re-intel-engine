"""
PDF Report Generator -- STRIKERS_PROTOCOL
Uses fpdf2 -- ASCII safe, no unicode issues
"""
import os, re
from datetime import datetime
from fpdf import FPDF


def clean(text):
    """Strip markdown + replace unicode with ASCII for FPDF Helvetica."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'`(.*?)`',       r'\1', text)
    text = re.sub(r'\*(.*?)\*',     r'\1', text)
    uni = {
        '\u2014':'--', '\u2013':'-',  '\u2018':"'", '\u2019':"'",
        '\u201c':'"',  '\u201d':'"',  '\u2022':'*', '\u2026':'...',
        '\u2192':'->', '\u2190':'<-', '\u00b0':'deg','\u03a9':'Ohm',
        '\u00b5':'u',  '\u00b7':'.',  '\u2248':'~',  '\u00d7':'x',
        '\u00f7':'/',  '\u2264':'<=', '\u2265':'>=', '\u2260':'!=',
    }
    for u, a in uni.items():
        text = text.replace(u, a)
    return text.encode('ascii', errors='ignore').decode('ascii').strip()


class GSReport(FPDF):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.set_auto_page_break(auto=True, margin=16)

    def header(self):
        self.set_fill_color(4, 8, 20)
        self.rect(0, 0, 210, 16, 'F')
        self.set_xy(10, 4)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(6, 182, 212)
        self.cell(0, 8, 'GHOST SIGNAL  |  STRIKERS_PROTOCOL', align='L')
        self.set_font('Helvetica', '', 7)
        self.set_text_color(30, 52, 64)
        self.set_xy(0, 4)
        self.cell(200, 8, 'OPERATOR: ' + clean(self.username).upper(), align='R')

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(30, 52, 64)
        ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        self.cell(0, 8, 'Page ' + str(self.page_no()) + '  |  ' + ts + '  |  FOR SECURITY RESEARCH & LEARNING ONLY', align='C')


def generate_pdf(analysis_id, username, target_type, analysis_mode,
                 file_name, result_md, risk_level, complexity,
                 confidence, tokens_used, reports_dir='./reports'):

    os.makedirs(reports_dir, exist_ok=True)
    pdf = GSReport(username)
    pdf.add_page()

    # Cover block
    pdf.set_fill_color(6, 12, 26)
    pdf.rect(10, 18, 190, 40, 'F')
    pdf.set_xy(14, 22)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(0, 9, 'GHOST SIGNAL -- INTELLIGENCE REPORT', ln=True)
    pdf.set_x(14)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 80, 100)
    pdf.cell(0, 6, 'Target: ' + clean(file_name or 'Manual Input') + '  |  Type: ' + clean(target_type).upper() + '  |  Mode: ' + clean(analysis_mode).upper(), ln=True)
    pdf.set_x(14)
    pdf.cell(0, 6, 'Risk: ' + clean(risk_level) + '  |  Complexity: ' + clean(complexity) + '  |  Confidence: ' + str(round(confidence)) + '%  |  Tokens: ' + str(tokens_used), ln=True)
    pdf.set_x(14)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(20, 52, 64)
    pdf.cell(0, 6, 'Generated: ' + datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC') + '  |  Report ID: GS-' + str(analysis_id).zfill(6), ln=True)
    pdf.ln(10)

    lines    = result_md.split('\n')
    in_code  = False
    in_table = False
    t_rows   = []

    def flush_table():
        if not t_rows:
            return
        valid = [r for r in t_rows if not re.match(r'^[\s|:\-]+$', r)]
        if not valid:
            t_rows.clear()
            return
        first_cells = [c.strip() for c in valid[0].split('|') if c.strip()]
        col_w = max(20, 185 // max(len(first_cells), 1))
        for ri, row in enumerate(valid):
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if not cells:
                continue
            pdf.set_x(12)
            if ri == 0:
                pdf.set_fill_color(6, 20, 40)
                pdf.set_font('Helvetica', 'B', 8)
                pdf.set_text_color(6, 182, 212)
            elif ri % 2 == 0:
                pdf.set_fill_color(4, 10, 22)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(120, 150, 160)
            else:
                pdf.set_fill_color(6, 14, 28)
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(120, 150, 160)
            for cell in cells:
                pdf.cell(col_w, 6, clean(cell)[:40], border=0, fill=True)
            pdf.ln()
        pdf.ln(3)
        t_rows.clear()

    for line in lines:
        if line.startswith('```'):
            if in_code:
                in_code = False
                pdf.ln(2)
            else:
                if in_table:
                    flush_table()
                    in_table = False
                in_code = True
            continue

        if in_code:
            pdf.set_x(14)
            pdf.set_font('Courier', '', 7)
            pdf.set_text_color(6, 182, 212)
            pdf.set_fill_color(2, 6, 16)
            pdf.cell(182, 5, clean(line)[:100], fill=True, ln=True)
            continue

        if line.startswith('| '):
            in_table = True
            t_rows.append(line)
            continue

        if in_table:
            flush_table()
            in_table = False

        if line.startswith('## '):
            pdf.ln(4)
            pdf.set_fill_color(4, 16, 32)
            pdf.set_x(10)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(6, 182, 212)
            pdf.cell(190, 8, '  ' + clean(line[3:]).upper(), fill=True, ln=True)
            pdf.ln(2)

        elif re.match(r'^\*\*.*\*\*$', line.strip()):
            pdf.set_x(12)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(200, 220, 230)
            pdf.cell(0, 6, clean(line), ln=True)

        elif line.startswith(('- ', '* ', '+ ', '-- ', '-- ')):
            pdf.set_x(16)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(100, 140, 160)
            pdf.cell(5, 5, '-', ln=False)
            pdf.set_x(21)
            pdf.multi_cell(174, 5, clean(line[2:]))

        elif re.match(r'^\d+\.', line):
            num = re.match(r'^(\d+)', line).group(1)
            txt = re.sub(r'^\d+\.\s*', '', line)
            pdf.set_x(12)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(6, 182, 212)
            pdf.cell(8, 5, num + '.', ln=False)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(100, 140, 160)
            pdf.multi_cell(174, 5, clean(txt))

        elif line.strip():
            pdf.set_x(12)
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(100, 140, 160)
            pdf.multi_cell(186, 5, clean(line))

        else:
            if not in_table:
                pdf.ln(2)

    if in_table:
        flush_table()

    out = os.path.join(reports_dir, 'gs-report-' + str(analysis_id).zfill(6) + '-' + clean(username) + '.pdf')
    pdf.output(out)
    return out
