const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, SimpleField, PageBreak, LevelFormat,
  TabStopType, TabStopPosition
} = require('docx');
const fs = require('fs');

// ── Read data passed as JSON file ─────────────────────────────────────────────
const dataPath = process.argv[2];
const outPath  = process.argv[3];
if (!dataPath || !outPath) {
  console.error('Usage: node generate_report.js data.json output.docx');
  process.exit(1);
}
const D = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

// ── Helpers ───────────────────────────────────────────────────────────────────
const PAGE_W   = 12240;  // US Letter
const PAGE_H   = 15840;
const MARGIN   = 900;    // 0.625"
const CONTENT_W = PAGE_W - MARGIN * 2; // 10440 DXA

const BLUE      = "1F4E79";
const LIGHT_BLU = "D6E4F0";
const MID_BLU   = "2E75B6";
const GREY_HDR  = "404040";
const GREEN     = "1D6A39";
const RED       = "C00000";
const WHITE     = "FFFFFF";
const LIGHT_GRY = "F2F2F2";

const border1 = (color = "BBBBBB") => ({ style: BorderStyle.SINGLE, size: 4, color });
const cellBorders = (color = "BBBBBB") => ({
  top: border1(color), bottom: border1(color),
  left: border1(color), right: border1(color)
});
const noBorder = () => ({
  top:    { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left:   { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right:  { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
});

function cell(text, opts = {}) {
  const {
    bold = false, color = "000000", bg = null, shade = false,
    align = AlignmentType.CENTER, colSpan, w, size = 18,
    italic = false, vAlign = VerticalAlign.CENTER
  } = opts;
  return new TableCell({
    columnSpan: colSpan,
    width: w ? { size: w, type: WidthType.DXA } : undefined,
    borders: shade ? cellBorders(MID_BLU) : cellBorders(),
    shading: bg ? { fill: bg, type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    verticalAlign: vAlign,
    children: [new Paragraph({
      alignment: align,
      spacing: { before: 0, after: 0 },
      children: [new TextRun({
        text: String(text ?? ""),
        bold, italic,
        color,
        size,
        font: "Arial"
      })]
    })]
  });
}

function hdrCell(text, opts = {}) {
  return cell(text, { bold: true, color: WHITE, bg: BLUE, size: 18, shade: false, ...opts, borders: cellBorders(BLUE) });
}

function subHdrCell(text, opts = {}) {
  return cell(text, { bold: true, color: WHITE, bg: MID_BLU, size: 17, ...opts });
}

function para(text, opts = {}) {
  const { bold = false, size = 20, color = "000000", align = AlignmentType.LEFT,
          before = 60, after = 60, italic = false } = opts;
  return new Paragraph({
    alignment: align,
    spacing: { before, after },
    children: [new TextRun({ text, bold, size, color, font: "Arial", italic })]
  });
}

function sectionHeading(num, title) {
  return new Paragraph({
    spacing: { before: 200, after: 100 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLU, space: 1 } },
    children: [
      new TextRun({ text: `${num}.  `, bold: true, size: 24, color: BLUE, font: "Arial" }),
      new TextRun({ text: title,       bold: true, size: 24, color: BLUE, font: "Arial" }),
    ]
  });
}

function spacer(pts = 80) {
  return new Paragraph({ spacing: { before: pts, after: 0 }, children: [] });
}

function fmtNum(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return Number(n).toLocaleString('en-IN');
}

function fmtCr(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return "₹" + Number(n / 1e7).toFixed(2);
}

function fmtPct(a, b) {
  if (!b || b === 0) return "—";
  return "+" + ((a - b) / b * 100).toFixed(1) + "%";
}

function fmtDiff(a, b) {
  const d = a - b;
  return d >= 0 ? "+" + fmtNum(d) : fmtNum(d);
}

function fmtDiffCr(a, b) {
  const d = (a - b) / 1e7;
  return (d >= 0 ? "+" : "") + "₹" + Math.abs(d).toFixed(2);
}

// ── Pull data ─────────────────────────────────────────────────────────────────
const m1Label   = D.m1_label;   // e.g. "March 2026"
const m2Label   = D.m2_label;   // e.g. "April 2026"
const m1End     = D.m1_end;     // e.g. "31 March 2026"
const m2End     = D.m2_end;     // e.g. "30 April 2026"
const reportDate= D.report_date; // e.g. "May 2026"

const S = D.snapshot; // { m1: {...}, m2: {...} }

// ── HEADER / FOOTER ───────────────────────────────────────────────────────────
const headerPara = [
  new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: 0, after: 60 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLU, space: 4 } },
    children: [
      new TextRun({ text: "24x7 Moneyworks Consulting Pvt. Ltd. (BankBenchers)  |  eKisanCredit Platform", size: 16, color: GREY_HDR, font: "Arial", italic: true }),
      new TextRun({ text: "   |   CONFIDENTIAL", size: 16, color: RED, font: "Arial", bold: true }),
    ]
  })
];

const footerPara = [
  new Paragraph({
    alignment: AlignmentType.LEFT,
    border: { top: { style: BorderStyle.SINGLE, size: 6, color: MID_BLU, space: 4 } },
    spacing: { before: 60, after: 0 },
    tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
    children: [
      new TextRun({ text: "Page ", size: 16, color: GREY_HDR, font: "Arial" }),
      new SimpleField('PAGE'),
      new TextRun({ text: `\teKCC Progress Report — ${m1Label} & ${m2Label}`, size: 16, color: GREY_HDR, font: "Arial" }),
    ]
  })
];

// ── COVER BLOCK ───────────────────────────────────────────────────────────────
function makeCover() {
  return [
    spacer(120),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
      children: [new TextRun({ text: "eKisanCredit (eKCC) Platform", bold: true, size: 36, color: BLUE, font: "Arial" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 40 },
      children: [new TextRun({ text: `Onboarding Progress Report — ${m1Label} & ${m2Label}`, bold: true, size: 28, color: MID_BLU, font: "Arial" })]
    }),
    spacer(60),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 40 },
      border: {
        top:    { style: BorderStyle.SINGLE, size: 6, color: MID_BLU },
        bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLU }
      },
      children: [new TextRun({ text: `Prepared by: 24x7 Moneyworks Consulting Pvt. Ltd. (BankBenchers)`, size: 20, font: "Arial", color: "333333" })]
    }),
    spacer(40),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: `Date: ${reportDate}     |     Submitted to: NABARD`, size: 20, font: "Arial", color: "555555" })]
    }),
    spacer(120),
  ];
}

// ── SECTION 1: At a Glance ────────────────────────────────────────────────────
function makeSection1() {
  const m1 = S.m1;
  const m2 = S.m2;

  // Col widths: Stage | M1 Apps | M1 Amt | M2 Apps | M2 Amt
  const cw = [2600, 1960, 1960, 1960, 1960];
  const tw = cw.reduce((a, b) => a + b, 0);

  const rows1 = [
    // Header row 1 — month labels spanning
    new TableRow({
      tableHeader: true,
      children: [
        hdrCell("Stage", { w: cw[0], vAlign: VerticalAlign.CENTER }),
        hdrCell(`As on ${m1End}`, { colSpan: 2, w: cw[1] + cw[2] }),
        hdrCell(`As on ${m2End}`, { colSpan: 2, w: cw[3] + cw[4] }),
      ]
    }),
    // Header row 2 — sub columns
    new TableRow({
      tableHeader: true,
      children: [
        hdrCell("", { w: cw[0] }),
        subHdrCell("Applications", { w: cw[1] }),
        subHdrCell("Amount (₹ Cr)", { w: cw[2] }),
        subHdrCell("Applications", { w: cw[3] }),
        subHdrCell("Amount (₹ Cr)", { w: cw[4] }),
      ]
    }),
    ...[
      ["In-Principle Approved", m1.ip_count, m1.ip_amt, m2.ip_count, m2.ip_amt],
      ["Sanctioned",            m1.sanction_count, m1.sanction_amt, m2.sanction_count, m2.sanction_amt],
      ["Disbursed",             m1.disb_count, m1.disb_amt, m2.disb_count, m2.disb_amt],
    ].map((r, i) => new TableRow({
      children: [
        cell(r[0], { bold: true, align: AlignmentType.LEFT, w: cw[0], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        cell(fmtNum(r[1]), { w: cw[1], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        cell(fmtCr(r[2]),  { w: cw[2], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        cell(fmtNum(r[3]), { bold: true, w: cw[3], bg: i % 2 === 1 ? LIGHT_BLU : "E8F4FD" }),
        cell(fmtCr(r[4]),  { bold: true, w: cw[4], bg: i % 2 === 1 ? LIGHT_BLU : "E8F4FD" }),
      ]
    }))
  ];

  const table1 = new Table({ width: { size: tw, type: WidthType.DXA }, columnWidths: cw, rows: rows1 });

  // MoM increment table
  const cw2 = [2600, 2613, 2613, 2614];
  const tw2 = cw2.reduce((a, b) => a + b, 0);
  const rows2 = [
    new TableRow({
      tableHeader: true,
      children: [
        hdrCell("Stage", { w: cw2[0] }),
        hdrCell("Net Increase (Applications)", { w: cw2[1] }),
        hdrCell("Net Increase (Amount ₹ Cr)",  { w: cw2[2] }),
        hdrCell("Growth %",                     { w: cw2[3] }),
      ]
    }),
    ...[
      ["In-Principle Approved", m1.ip_count,       m1.ip_amt,       m2.ip_count,       m2.ip_amt],
      ["Sanctioned",            m1.sanction_count,  m1.sanction_amt, m2.sanction_count,  m2.sanction_amt],
      ["Disbursed",             m1.disb_count,      m1.disb_amt,     m2.disb_count,      m2.disb_amt],
    ].map((r, i) => {
      const diffN = r[3] - r[1];
      const diffA = r[4] - r[2];
      const pct   = r[1] > 0 ? ((diffN / r[1]) * 100).toFixed(1) : "—";
      const sign  = diffN >= 0 ? "+" : "";
      return new TableRow({
        children: [
          cell(r[0], { bold: true, align: AlignmentType.LEFT, w: cw2[0], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(`${sign}${fmtNum(diffN)}`,     { bold: true, color: diffN >= 0 ? GREEN : RED, w: cw2[1], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(fmtDiffCr(r[4], r[2]),          { bold: true, color: diffA >= 0 ? GREEN : RED, w: cw2[2], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(diffN >= 0 ? `+${pct}%` : `${pct}%`, { bold: true, color: diffN >= 0 ? GREEN : RED, w: cw2[3], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        ]
      });
    })
  ];
  const table2 = new Table({ width: { size: tw2, type: WidthType.DXA }, columnWidths: cw2, rows: rows2 });

  return [
    sectionHeading("1", "Platform Onboarding Position — At a Glance"),
    para(`The following table captures cumulative in-principle approvals, sanctions, and disbursements processed through the eKCC platform for ${m1Label} and ${m2Label}.`, { before: 80, after: 100 }),
    table1,
    spacer(120),
    para(`Month-on-Month Increment (${m2Label} over ${m1Label})`, { bold: true, size: 20, before: 80, after: 80 }),
    table2,
    spacer(80),
  ];
}

// ── SECTION 2: Geographic & Institutional Reach ───────────────────────────────
function makeSection2() {
  const m1 = S.m1;
  const m2 = S.m2;

  const cw = [4500, 2970, 2970];
  const tw = cw.reduce((a, b) => a + b, 0);

  const rows = [
    new TableRow({
      tableHeader: true,
      children: [
        hdrCell("Parameter", { w: cw[0], align: AlignmentType.LEFT }),
        hdrCell(`As on ${m1End}`, { w: cw[1] }),
        hdrCell(`As on ${m2End}`, { w: cw[2] }),
      ]
    }),
    ...[
      ["States / UTs with active transactions",            m1.active_states,   m2.active_states],
      ["Banks actively processing on platform",            m1.active_banks,    m2.active_banks],
      ["Banks with zero transactions (contracted but inactive)", m1.zero_banks, m2.zero_banks],
    ].map((r, i) => new TableRow({
      children: [
        cell(r[0], { align: AlignmentType.LEFT, w: cw[0], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        cell(fmtNum(r[1]), { w: cw[1], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        cell(fmtNum(r[2]), { bold: true, w: cw[2], bg: i % 2 === 1 ? LIGHT_BLU : "E8F4FD" }),
      ]
    }))
  ];

  const zeroNote = D.zero_banks_note || "";

  return [
    sectionHeading("2", "Geographic & Institutional Reach"),
    new Table({ width: { size: tw, type: WidthType.DXA }, columnWidths: cw, rows }),
    spacer(80),
    new Paragraph({
      spacing: { before: 60, after: 60 },
      children: [
        new TextRun({ text: "Note: ", bold: true, size: 18, font: "Arial", color: "555555" }),
        new TextRun({ text: zeroNote, size: 18, font: "Arial", italic: true, color: "555555" }),
      ]
    }),
    spacer(80),
  ];
}

// ── SECTION 3: Top 10 States ─────────────────────────────────────────────────
function makeSection3() {
  const states = D.top_states; // array of { rank, state, m1_count, m2_count, m2_amt }
  const cw = [540, 2800, 1620, 1620, 1620, 1620];
  const tw = cw.reduce((a, b) => a + b, 0);

  const rows = [
    new TableRow({
      tableHeader: true,
      children: [
        hdrCell("#",           { w: cw[0] }),
        hdrCell("State",       { w: cw[1], align: AlignmentType.LEFT }),
        hdrCell(`As on ${m1End}`, { w: cw[2] }),
        hdrCell(`As on ${m2End}`, { w: cw[3] }),
        hdrCell("Net Increase",   { w: cw[4] }),
        hdrCell(`${m2Label} Amount (₹ Cr)`, { w: cw[5] }),
      ]
    }),
    ...states.map((r, i) => {
      const diff = r.m2_count - r.m1_count;
      const diffStr = diff === 0 ? "—" : (diff > 0 ? "+" + fmtNum(diff) : fmtNum(diff));
      return new TableRow({
        children: [
          cell(r.rank,          { w: cw[0], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(r.state,         { align: AlignmentType.LEFT, bold: true, w: cw[1], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(fmtNum(r.m1_count), { w: cw[2], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(fmtNum(r.m2_count), { bold: true, w: cw[3], bg: i % 2 === 1 ? LIGHT_BLU : "E8F4FD" }),
          cell(diffStr,         { bold: true, color: diff >= 0 ? GREEN : RED, w: cw[4], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(fmtCr(r.m2_amt), { w: cw[5], bg: i % 2 === 1 ? LIGHT_GRY : null }),
        ]
      });
    })
  ];

  return [
    sectionHeading("3", "Top 10 States — In-Principle Applications"),
    para(`Ranked by ${m2Label} in-principle application volume.`, { before: 80, after: 100, italic: true, size: 18, color: "555555" }),
    new Table({ width: { size: tw, type: WidthType.DXA }, columnWidths: cw, rows }),
    spacer(80),
  ];
}

// ── SECTION 4: Bank Count by Band ─────────────────────────────────────────────
function makeSection4() {
  const bands = D.bands; // { band, m1_count, m2_count, note }
  const cw = [3200, 2620, 2620, 2000];  // adjusted — note column
  const tw = cw.reduce((a, b) => a + b, 0);

  // Check if note column has any content
  const hasNotes = bands.some(b => b.note);
  const usedCw   = hasNotes ? cw : [3500, 3000, 3000];
  const usedTw   = usedCw.reduce((a, b) => a + b, 0);

  const hdrRow = new TableRow({
    tableHeader: true,
    children: [
      hdrCell("Application Band",                      { w: usedCw[0], align: AlignmentType.LEFT }),
      hdrCell(`As on ${m1End} (Banks)`,                { w: usedCw[1] }),
      hdrCell(`As on ${m2End} (Banks)`,                { w: usedCw[2] }),
      ...(hasNotes ? [hdrCell("Movement", { w: usedCw[3] })] : []),
    ]
  });

  const dataRows = bands.map((r, i) => {
    const isTotal = r.band.toLowerCase().includes("total");
    return new TableRow({
      children: [
        cell(r.band,           { align: AlignmentType.LEFT, bold: isTotal, w: usedCw[0], bg: isTotal ? LIGHT_BLU : (i % 2 === 1 ? LIGHT_GRY : null) }),
        cell(fmtNum(r.m1_count), { bold: isTotal, w: usedCw[1], bg: isTotal ? LIGHT_BLU : (i % 2 === 1 ? LIGHT_GRY : null) }),
        cell(fmtNum(r.m2_count), { bold: isTotal, w: usedCw[2], bg: isTotal ? LIGHT_BLU : (i % 2 === 1 ? LIGHT_BLU : "E8F4FD") }),
        ...(hasNotes ? [cell(r.note || "", { align: AlignmentType.LEFT, w: usedCw[3], size: 16, bg: isTotal ? LIGHT_BLU : (i % 2 === 1 ? LIGHT_GRY : null) })] : []),
      ]
    });
  });

  return [
    sectionHeading("4", "Bank Count by Onboarding Application Band"),
    para("Distribution of active banks by cumulative in-principle application volume.", { before: 80, after: 100, italic: true, size: 18, color: "555555" }),
    new Table({ width: { size: usedTw, type: WidthType.DXA }, columnWidths: usedCw, rows: [hdrRow, ...dataRows] }),
    spacer(80),
  ];
}

// ── SECTION 5: Top 15 Banks ────────────────────────────────────────────────────
function makeSection5() {
  const banks = D.top_banks; // { rank, type, name, state, m1_count, m2_count, tag }
  const cw = [450, 650, 3000, 1600, 1180, 1180, 1180, 700];
  const tw = cw.reduce((a, b) => a + b, 0);

  const rows = [
    new TableRow({
      tableHeader: true,
      children: [
        hdrCell("Rk",          { w: cw[0] }),
        hdrCell("Type",        { w: cw[1] }),
        hdrCell("Bank Name",   { w: cw[2], align: AlignmentType.LEFT }),
        hdrCell("State",       { w: cw[3], align: AlignmentType.LEFT }),
        hdrCell(`As on ${m1End}`, { w: cw[4] }),
        hdrCell(`As on ${m2End}`, { w: cw[5] }),
        hdrCell("Net Increase",   { w: cw[6] }),
        hdrCell("Tag",         { w: cw[7] }),
      ]
    }),
    ...banks.map((r, i) => {
      const diff    = r.m2_count - r.m1_count;
      const diffStr = r.m1_count === 0 ? `+${fmtNum(r.m2_count)}` : (diff === 0 ? "—" : (diff > 0 ? "+" + fmtNum(diff) : fmtNum(diff)));
      const isNew   = r.m1_count === 0 && r.m2_count > 0;
      const tag     = isNew ? "New" : (r.tag || "");
      return new TableRow({
        children: [
          cell(r.rank,              { w: cw[0], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(r.type,              { w: cw[1], bg: i % 2 === 1 ? LIGHT_GRY : null, size: 16 }),
          cell(r.name,              { align: AlignmentType.LEFT, bold: true, w: cw[2], bg: i % 2 === 1 ? LIGHT_GRY : null, size: 17 }),
          cell(r.state,             { align: AlignmentType.LEFT, w: cw[3], bg: i % 2 === 1 ? LIGHT_GRY : null, size: 16 }),
          cell(r.m1_count === 0 ? "—" : fmtNum(r.m1_count), { w: cw[4], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(fmtNum(r.m2_count),  { bold: true, w: cw[5], bg: i % 2 === 1 ? LIGHT_BLU : "E8F4FD" }),
          cell(diffStr,             { bold: true, color: diff >= 0 ? GREEN : RED, w: cw[6], bg: i % 2 === 1 ? LIGHT_GRY : null }),
          cell(tag,                 { bold: isNew, color: isNew ? GREEN : "000000", w: cw[7], bg: i % 2 === 1 ? LIGHT_GRY : null, size: 16 }),
        ]
      });
    })
  ];

  // Standout performers paragraph
  const standouts = D.standouts || [];
  const standoutParas = [
    para("Standout performers (Net Increase — " + m2Label + " over " + m1Label + "):", { bold: true, before: 120, after: 60 }),
    ...standouts.map(s => new Paragraph({
      spacing: { before: 40, after: 40 },
      indent: { left: 360 },
      children: [
        new TextRun({ text: s.name + ": ", bold: true, size: 18, font: "Arial" }),
        new TextRun({ text: s.note,         size: 18,  font: "Arial" }),
      ]
    }))
  ];

  return [
    sectionHeading("5", "Top 15 Banks — In-Principle Applications"),
    para(`Ranked by ${m2Label} in-principle application volume, with ${m1Label} figures and net increase.`, { before: 80, after: 100, italic: true, size: 18, color: "555555" }),
    new Table({ width: { size: tw, type: WidthType.DXA }, columnWidths: cw, rows }),
    ...standoutParas,
    spacer(80),
  ];
}

// ── Assemble document ─────────────────────────────────────────────────────────
const children = [
  ...makeCover(),
  ...makeSection1(),
  ...makeSection2(),
  ...makeSection3(),
  ...makeSection4(),
  ...makeSection5(),
];

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Arial", size: 20, color: "000000" } }
    }
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN }
      }
    },
    headers: { default: new Header({ children: headerPara }) },
    footers: { default: new Footer({ children: footerPara }) },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log('OK:' + outPath);
}).catch(e => {
  console.error('ERROR:' + e.message);
  process.exit(1);
});