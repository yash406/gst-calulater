from flask import Flask, render_template, request, send_file, url_for, flash, redirect
import os
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import traceback

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# Indian states list
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal"
]

# Enhanced GST rates by category
gst_rates = {
    #  0% GST Items (Nil Rated / Exempt)
    'rice (unpackaged)': 0,
    'wheat (unpackaged)': 0,
    'milk (fresh)': 0,
    'vegetables (fresh)': 0,
    'fruits (fresh)': 0,
    'flour (unpackaged)': 0,
    'salt': 0,
    'potato': 0,
    'onion': 0,
    'tomato': 0,
    'apple (fresh)': 0,
    'banana (fresh)': 0,
    'orange (fresh)': 0,
    'prasad': 0,
    'educational services': 0,
    'health services': 0,
    'unbranded paneer': 0,
    'children\'s drawing & coloring books': 0,
    'sanitary napkins': 0,

    # 5% GST Items
    'sugar': 5,
    'tea (processed)': 5,
    'coffee (roasted beans)': 5,
    'spices': 5,
    'medicine': 5, #/ Many life-saving drugs are 5%
    'book': 5,
    'newspaper': 5,
    'milk powder': 5,
    'baby food': 5,
    'honey (packaged)': 5,
    'turmeric (powdered)': 5,
    'coriander (powdered)': 5,
    'cumin (powdered)': 5,
    'cardamom': 5,
    'cinnamon': 5,
    'rice (packaged/branded)': 5,
    'wheat (packaged/branded)': 5,
    'flour (packaged/branded)': 5,
    'paneer (packaged/branded)': 5,
    'coal': 5,
    'edible oils': 5,
    'domestic LPG': 5,
    'restaurants (non-AC, no alcohol)': 5, #// Note: This can vary, some restaurants might be 18% with ITC
    'footwear (< Rs.500)': 5,
    'apparels (< Rs.1000)': 5,
    'railway tickets (sleeper/non-AC)': 5,
    'air travel (economy)': 5,

    # 12% GST Items
    'processed food': 12,
    'ayurvedic (some preparations)': 12, #// Many medicines are 5%, but some specific Ayurvedic/Unani preparations can be 12%
    'butter': 12,
    'cheese': 12,
    'ghee': 12,
    'umbrella': 12,
    'spectacles': 12,
    'glasses': 12, #// Assuming spectacles/eyewear
    'exercise book': 12,
    'dried fruits': 12,
    'frozen vegetables': 12,
    'mobile phones': 18, #// IMPORTANT: Updated from 12% to 18%
    'computer': 18, #// IMPORTANT: Updated from 12% to 18%
    'laptop': 18, #// IMPORTANT: Updated from 12% to 18%
    'tablet': 18, #// IMPORTANT: Updated from 12% to 18%
    'processed vegetables': 12,
    'hotel (rent Rs. 1000-7500/day)': 12,

    #// 18% GST Items
    'electronics (general)': 18,
    'soap': 18,
    'toothpaste': 18,
    'shampoo': 18,
    'television': 18,
    'tv (up to 27 inches)': 18, #// Clarifying TV sizes
    'washing machine': 18,
    'refrigerator': 18,
    'microwave': 18,
    'iron': 18,
    'mixer': 18,
    'grinder': 18,
    'fan': 18,
    'cooler': 18,
    'restaurant (AC/alcohol)': 18, #// Differentiated from 5%
    'hotel (rent above Rs. 7500/day)': 18,
    'service (general)': 18, #// Default for most non-exempt services
    'software': 18,
    'app': 18,
    'website': 18,
    'design': 18,
    'consulting': 18,
    'repair': 18,
    'maintenance': 18,
    'hair oil': 18,
    'chocolates': 18,
    'ice cream': 18,
    'non-alcoholic beverages (packaged)': 18,

    #// 28% GST Items
    'car': 28, #// Plus cess depending on type
    'bike': 28,
    'motorcycle': 28, #// High-end motorcycles often have cess
    'ac (air conditioner)': 28,
    'cigarette': 28, #// Plus high cess
    'tobacco': 28, #// Plus high cess
    'luxury goods (general)': 28,
    'perfume': 28,
    'cosmetics': 28,
    'dishwasher': 28,
    'vacuum cleaner': 28,
    'water heater': 28,
    'cement': 28,
    'online gaming': 28,
    'carbonated beverages': 28, #// Plus cess
    'tv (above 27 inches)': 28, # If applicable for very large TVs
    'luxury cars': 28, # Plus high cess
    'sin goods': 28, # General category for items like tobacco, pan masala

    # Additional GST Rates
    'gold': 3,
    'precious stones': 3,
    'jewellery': 3,
    'Artificial jewellery items':3,
    'Rough diamonds':0.25,
    'uncut gems':0.25,
}

invoices = []

def validate_form_data(form_data):
    """Validate form data and return errors if any"""
    errors = []
    
    if not form_data.get('state_seller'):
        errors.append("Seller state is required")
    if not form_data.get('state_buyer'):
        errors.append("Buyer state is required")
    
    item_keys = [key for key in form_data.keys() if key.startswith('name_')]
    if not item_keys:
        errors.append("At least one item is required")
        return errors
    
    for key in item_keys:
        index = key.split('_')[1]
        name = form_data.get(f'name_{index}', '').strip()
        price = form_data.get(f'price_{index}', '')
        qty = form_data.get(f'qty_{index}', '')
        gst_rate = form_data.get(f'gst_rate_{index}', '')
        
        if not name:
            errors.append(f"Item {int(index)+1}: Name is required")
        
        try:
            price_val = float(price) if price else 0
            if price_val <= 0:
                errors.append(f"Item {int(index)+1}: Valid price is required")
        except ValueError:
            errors.append(f"Item {int(index)+1}: Invalid price format")
        
        try:
            qty_val = int(qty) if qty else 0
            if qty_val <= 0:
                errors.append(f"Item {int(index)+1}: Valid quantity is required")
        except ValueError:
            errors.append(f"Item {int(index)+1}: Invalid quantity format")
        
        if not gst_rate:
            errors.append(f"Item {int(index)+1}: GST rate is required")
        elif gst_rate == 'manual':
            manual_gst = form_data.get(f'gst_manual_{index}', '')
            try:
                manual_val = float(manual_gst) if manual_gst else -1
                if manual_val < 0 or manual_val > 100:
                    errors.append(f"Item {int(index)+1}: Manual GST rate must be between 0-100%")
            except ValueError:
                errors.append(f"Item {int(index)+1}: Invalid manual GST rate format")
    
    return errors

def extract_form_data(request_form):
    """Extract and organize form data"""
    form_data = {
        'state_seller': request_form.get('state_seller', ''),
        'state_buyer': request_form.get('state_buyer', ''),
        'items': []
    }
    
    item_keys = [key for key in request_form.keys() if key.startswith('name_')]
    item_indices = sorted(set(int(k.split('_')[1]) for k in item_keys))
    
    for i in item_indices:
        name = request_form.get(f'name_{i}', '').strip()
        if name:
            item_data = {
                'name': name,
                'qty': request_form.get(f'qty_{i}', '1'),
                'price': request_form.get(f'price_{i}', ''),
                'gst_rate': request_form.get(f'gst_rate_{i}', ''),
                'gst_manual': request_form.get(f'gst_manual_{i}', ''),
                'price_type': request_form.get(f'price_type_{i}', 'exclusive')
            }
            form_data['items'].append(item_data)
    
    return form_data

def generate_enhanced_pdf(invoice_data, invoice_id, bar_chart=None, pie_chart=None, line_chart=None):
    """Generate an enhanced, professional PDF invoice"""
    try:
        os.makedirs('invoices', exist_ok=True)
        pdf_filename = f"invoices/invoice_{invoice_id}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2c3e50'),
            alignment=1,  # Center alignment
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=HexColor('#34495e'),
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            textColor=HexColor('#2c3e50')
        )
        
        # Build PDF content
        story = []
        
        # Header
        story.append(Paragraph("🧾 GST INVOICE", title_style))
        story.append(Spacer(1, 12))
        
        # Invoice details table
        invoice_details = [
            ['Invoice ID:', f'#{invoice_id}'],
            ['Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['GST Type:', f'{invoice_data["gst_type"].upper()}-STATE'],
            ['Status:', 'PAID' if invoice_data['total'] > 0 else 'DRAFT']
        ]
        
        details_table = Table(invoice_details, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [HexColor('#ffffff'), HexColor('#f8f9fa')])
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Items heading
        story.append(Paragraph("📦 INVOICE ITEMS", heading_style))
        story.append(Spacer(1, 12))
        
        # Items table
        items_data = [['Item Name', 'Qty', 'Price (₹)', 'GST Rate (%)', 'GST Amount (₹)', 'Total (₹)']]
        
        for item in invoice_data['items']:
            total_price = item['item_total'] + item['item_gst']
            items_data.append([
                item['name'][:25] + ('...' if len(item['name']) > 25 else ''),
                str(item['qty']),
                f"{item['price']:.2f}",
                f"{item['gst_rate']:.1f}%",
                f"{item['item_gst']:.2f}",
                f"{total_price:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[2.5*inch, 0.7*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Item names left-aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            
            # Data rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Total column highlighting
            ('BACKGROUND', (-1, 1), (-1, -1), HexColor('#e8f5e8')),
            ('FONTNAME', (-1, 1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Summary section
        story.append(Paragraph("💰 INVOICE SUMMARY", heading_style))
        story.append(Spacer(1, 12))
        
        # Summary table
        summary_data = [
            ['Subtotal:', f"₹{invoice_data['subtotal']:.2f}"]
        ]
        
        if invoice_data['gst_type'] == 'intra':
            summary_data.extend([
                ['CGST:', f"₹{invoice_data['total_cgst']:.2f}"],
                ['SGST:', f"₹{invoice_data['total_sgst']:.2f}"]
            ])
        else:
            summary_data.append(['IGST:', f"₹{invoice_data['total_igst']:.2f}"])
        
        summary_data.extend([
            ['Total GST:', f"₹{invoice_data['gst_total']:.2f}"],
            ['', ''],  # Empty row for spacing
            ['FINAL TOTAL:', f"₹{invoice_data['total']:.2f}"]
        ])
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (0, -1), (-1, -1), HexColor('#e74c3c')),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#fff5f5')),
            ('GRID', (0, 0), (-1, -2), 1, HexColor('#bdc3c7')),
            ('BOX', (0, -1), (-1, -1), 2, HexColor('#e74c3c')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Add charts if available
        if bar_chart and os.path.exists(bar_chart):
            story.append(Paragraph("📊 GST ANALYSIS CHARTS", heading_style))
            story.append(Spacer(1, 12))
            
            # Create a table for charts
            chart_data = []
            chart_row = []
            
            if bar_chart and os.path.exists(bar_chart):
                chart_row.append(Image(bar_chart, width=2*inch, height=1.5*inch))
            
            if pie_chart and os.path.exists(pie_chart):
                chart_row.append(Image(pie_chart, width=2*inch, height=1.5*inch))
            
            if line_chart and os.path.exists(line_chart):
                chart_row.append(Image(line_chart, width=2*inch, height=1.5*inch))
            
            if chart_row:
                chart_data.append(chart_row)
                charts_table = Table(chart_data)
                charts_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(charts_table)
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        <para align="center">
        <font size="8" color="#7f8c8d">
        Generated by GST Invoice System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        This is a computer-generated invoice and does not require a signature.
        </font>
        </para>
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return pdf_filename
        
    except Exception as e:
        print(f"Error generating enhanced PDF: {e}")
        traceback.print_exc()
        return None

def generate_invoice_file(invoice_data, invoice_id, bar_chart=None, pie_chart=None, line_chart=None):
    """Generate text and enhanced PDF invoice files"""
    os.makedirs('invoices', exist_ok=True)
    txt_filename = f"invoices/invoice_{invoice_id}.txt"

    # Generate text invoice
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("                    GST INVOICE                    \n")
        f.write("=" * 60 + "\n")
        f.write(f"Invoice ID: {invoice_id}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"GST Type: {invoice_data['gst_type'].upper()}-STATE\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("ITEMS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Item':<25} {'Qty':<5} {'Price':<10} {'GST%':<8} {'GST Amt':<10} {'Total':<10}\n")
        f.write("-" * 80 + "\n")
        
        for item in invoice_data['items']:
            total_price = item['item_total'] + item['item_gst']
            f.write(f"{item['name'][:24]:<25} {item['qty']:<5} {item['price']:<10.2f} {item['gst_rate']:<8.1f} {item['item_gst']:<10.2f} {total_price:<10.2f}\n")
        
        f.write("-" * 80 + "\n")
        f.write(f"\n{'SUMMARY:':<40}\n")
        f.write(f"{'Subtotal:':<25} ₹{invoice_data['subtotal']:.2f}\n")
        
        if invoice_data['gst_type'] == 'intra':
            f.write(f"{'CGST:':<25} ₹{invoice_data['total_cgst']:.2f}\n")
            f.write(f"{'SGST:':<25} ₹{invoice_data['total_sgst']:.2f}\n")
        else:
            f.write(f"{'IGST:':<25} ₹{invoice_data['total_igst']:.2f}\n")
        
        f.write(f"{'Total GST:':<25} ₹{invoice_data['gst_total']:.2f}\n")
        f.write("=" * 60 + "\n")
        f.write(f"{'FINAL TOTAL:':<25} ₹{invoice_data['total']:.2f}\n")
        f.write("=" * 60 + "\n")

    # Generate enhanced PDF
    pdf_filename = generate_enhanced_pdf(invoice_data, invoice_id, bar_chart, pie_chart, line_chart)
    
    return txt_filename, pdf_filename

def generate_gst_graphs(invoice_data, invoice_id):
    """Generate enhanced GST analysis charts"""
    try:
        os.makedirs('static/graphs', exist_ok=True)

        items = invoice_data['items']
        gst_type = invoice_data.get('gst_type', 'intra')

        base_price = sum(item['item_total'] for item in items)
        gst_total = sum(item['item_gst'] for item in items)

        # Set up color scheme
        colors_scheme = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

        if gst_type == 'intra':
            cgst = gst_total / 2
            sgst = gst_total / 2
            labels = ['Base Price', 'CGST', 'SGST']
            values = [base_price, cgst, sgst]
            colors = colors_scheme[:3]
        else:
            igst = gst_total
            labels = ['Base Price', 'IGST']
            values = [base_price, igst]
            colors = colors_scheme[:2]

        # Enhanced Bar chart
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(labels, values, color=colors, alpha=0.8, edgecolor='white', linewidth=2)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                   f'₹{value:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
        
        ax.set_title('GST Components Analysis - Bar Chart', fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel('Amount (₹)', fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_facecolor('#f8f9fa')
        
        # Add gradient effect
        for bar, color in zip(bars, colors):
            bar.set_facecolor(color)
        
        plt.tight_layout()
        bar_path = f'static/graphs/bar_{invoice_id}.png'
        plt.savefig(bar_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        # Enhanced Pie chart
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', 
                                         colors=colors, startangle=90, 
                                         explode=[0.05]*len(values),
                                         shadow=True, textprops={'fontsize': 11})
        
        # Enhance text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(12)
        
        for text in texts:
            text.set_fontweight('bold')
            text.set_fontsize(12)
        
        ax.set_title('GST Distribution - Pie Chart', fontsize=16, fontweight='bold', pad=20)
        
        # Add legend with values
        legend_labels = [f'{label}: ₹{value:.2f}' for label, value in zip(labels, values)]
        ax.legend(wedges, legend_labels, title="Components", loc="center left", 
                 bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)
        
        plt.tight_layout()
        pie_path = f'static/graphs/pie_{invoice_id}.png'
        plt.savefig(pie_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        # Enhanced Line chart
        fig, ax = plt.subplots(figsize=(12, 7))
        multipliers = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4]
        base_prices = [base_price * m for m in multipliers]
        
        if gst_type == 'intra':
            avg_gst_rate = sum(item['gst_rate'] for item in items) / len(items) if items else 0
            cgst_rate = sgst_rate = avg_gst_rate / 2
            cgst_vals = [p * cgst_rate / 100 for p in base_prices]
            sgst_vals = [p * sgst_rate / 100 for p in base_prices]
            total_gst_vals = [c + s for c, s in zip(cgst_vals, sgst_vals)]
            
            ax.plot(base_prices, cgst_vals, marker='o', linewidth=3, label='CGST', 
                   color=colors_scheme[1], markersize=8, alpha=0.8)
            ax.plot(base_prices, sgst_vals, marker='s', linewidth=3, label='SGST', 
                   color=colors_scheme[2], markersize=8, alpha=0.8)
            ax.plot(base_prices, total_gst_vals, marker='^', linewidth=4, label='Total GST', 
                   color=colors_scheme[0], markersize=10, alpha=0.9)
            ax.set_title(f'GST Trend Analysis (Avg Rate: {avg_gst_rate:.1f}%)', 
                        fontsize=16, fontweight='bold', pad=20)
        else:
            avg_gst_rate = sum(item['gst_rate'] for item in items) / len(items) if items else 0
            igst_vals = [p * avg_gst_rate / 100 for p in base_prices]
            ax.plot(base_prices, igst_vals, marker='o', linewidth=4, label='IGST', 
                   color=colors_scheme[1], markersize=10, alpha=0.9)
            ax.set_title(f'IGST Trend Analysis (Avg Rate: {avg_gst_rate:.1f}%)', 
                        fontsize=16, fontweight='bold', pad=20)
        
        ax.set_xlabel('Base Price (₹)', fontsize=12, fontweight='bold')
        ax.set_ylabel('GST Amount (₹)', fontsize=12, fontweight='bold')
        ax.legend(fontsize=11, loc='upper left')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_facecolor('#f8f9fa')
        
        # Add annotations for key points
        if base_prices and (cgst_vals if gst_type == 'intra' else igst_vals):
            current_point = len(base_prices) // 2
            current_price = base_prices[current_point]
            current_gst = total_gst_vals[current_point] if gst_type == 'intra' else igst_vals[current_point]
            ax.annotate(f'Current: ₹{current_gst:.2f}', 
                       xy=(current_price, current_gst), 
                       xytext=(current_price * 1.2, current_gst * 1.2),
                       arrowprops=dict(arrowstyle='->', color='red', lw=2),
                       fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.7))
        
        plt.tight_layout()
        line_path = f'static/graphs/line_{invoice_id}.png'
        plt.savefig(line_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return bar_path, pie_path, line_path
    
    except Exception as e:
        print(f"Error generating graphs: {e}")
        traceback.print_exc()
        return None, None, None

@app.route('/')
def index():
    return render_template('index.html', 
                         gst_rates=gst_rates, 
                         states=INDIAN_STATES,
                         form_data=None,
                         error=None)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Extract form data
        form_data = extract_form_data(request.form)
        
        # Validate form data
        errors = validate_form_data(request.form)
        if errors:
            error_message = "; ".join(errors)
            return render_template('index.html', 
                                 gst_rates=gst_rates, 
                                 states=INDIAN_STATES,
                                 form_data=form_data,
                                 error=error_message)

        # Process items
        items = []
        subtotal = 0
        gst_total = 0

        state_seller = request.form['state_seller']
        state_buyer = request.form['state_buyer']
        gst_type = 'intra' if state_seller.strip().lower() == state_buyer.strip().lower() else 'inter'

        # Get all item indices
        item_keys = [key for key in request.form.keys() if key.startswith('name_')]
        item_indices = sorted(set(int(k.split('_')[1]) for k in item_keys))

        for i in item_indices:
            name = request.form.get(f'name_{i}', '').strip()
            if not name:
                continue
                
            try:
                price = float(request.form.get(f'price_{i}', 0))
                qty = int(request.form.get(f'qty_{i}', 1))
            except ValueError:
                continue

            gst_rate_sel = request.form.get(f'gst_rate_{i}')
            gst_rate = 0.0

            if gst_rate_sel == 'manual':
                try:
                    gst_rate = float(request.form.get(f'gst_manual_{i}', 0))
                except ValueError:
                    gst_rate = 0
            else:
                try:
                    gst_rate = float(gst_rate_sel)
                except ValueError:
                    gst_rate = 0

            price_type = request.form.get(f'price_type_{i}', 'exclusive')

            # Calculate based on price type
            if price_type == 'inclusive':
                # Price includes GST
                base_price_per_unit = price / (1 + gst_rate/100)
                gst_amount_per_unit = price - base_price_per_unit
            else:
                # Price excludes GST
                base_price_per_unit = price
                gst_amount_per_unit = price * gst_rate / 100

            item_total = base_price_per_unit * qty
            item_gst = gst_amount_per_unit * qty

            items.append({
                'name': name,
                'price': round(base_price_per_unit, 2),
                'qty': qty,
                'gst_rate': gst_rate,
                'item_total': round(item_total, 2),
                'item_gst': round(item_gst, 2),
                'price_type': price_type,
                'entered_price': price
            })

            subtotal += item_total
            gst_total += item_gst

        if not items:
            return render_template('index.html', 
                                 gst_rates=gst_rates, 
                                 states=INDIAN_STATES,
                                 form_data=form_data,
                                 error="No valid items found")

        total = subtotal + gst_total

        # Calculate GST breakdown
        if gst_type == 'intra':
            total_cgst = gst_total / 2
            total_sgst = gst_total / 2
            total_igst = 0
        else:
            total_cgst = 0
            total_sgst = 0
            total_igst = gst_total

        invoice_data = {
            'items': items,
            'subtotal': round(subtotal, 2),
            'gst_total': round(gst_total, 2),
            'total': round(total, 2),
            'gst_type': gst_type,
            'total_cgst': round(total_cgst, 2),
            'total_sgst': round(total_sgst, 2),
            'total_igst': round(total_igst, 2)
        }
        
        invoice_id = len(invoices) + 1
        invoices.append(invoice_data)

        # Generate charts
        bar_path, pie_path, line_path = generate_gst_graphs(invoice_data, invoice_id)

        # Generate invoice files
        invoice_txt, invoice_pdf = generate_invoice_file(invoice_data, invoice_id, bar_path, pie_path, line_path)

        return render_template('bill.html', 
                             data=invoice_data, 
                             invoice_id=invoice_id,
                             bar_chart=bar_path, 
                             pie_chart=pie_path, 
                             line_chart=line_path,
                             invoice_txt=invoice_txt, 
                             invoice_pdf=invoice_pdf,
                             timestamp=datetime.now())

    except Exception as e:
        print(f"Error in generate route: {e}")
        traceback.print_exc()
        return render_template('index.html', 
                             gst_rates=gst_rates, 
                             states=INDIAN_STATES,
                             form_data=form_data if 'form_data' in locals() else None,
                             error=f"An error occurred: {str(e)}")

@app.route('/download_txt/<int:invoice_id>')
def download_txt(invoice_id):
    try:
        filename = f"invoices/invoice_{invoice_id}.txt"
        if os.path.exists(filename):
            return send_file(filename, as_attachment=True)
        else:
            flash("Invoice file not found", "error")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error downloading file: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/download_pdf/<int:invoice_id>')
def download_pdf(invoice_id):   
    try:
        filename = f"invoices/invoice_{invoice_id}.pdf"
        if os.path.exists(filename):
            return send_file(filename, as_attachment=True)
        else:
            flash("Invoice file not found", "error")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error downloading file: {str(e)}", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('invoices', exist_ok=True)
    os.makedirs('static/graphs', exist_ok=True)
    app.run(host='0.0.0.0',debug=True)
