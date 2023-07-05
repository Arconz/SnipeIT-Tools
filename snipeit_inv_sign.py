from reportlab.platypus import SimpleDocTemplate, Flowable, Paragraph, Table, TableStyle
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
import requests
import pandas as pd
import configparser
import json
import html

# Register the Myriad Pro fonts
pdfmetrics.registerFont(TTFont('MyriadPro-Bold', 'fonts/MYRIADPRO-BOLD.TTF'))
pdfmetrics.registerFont(TTFont('MyriadPro-SemiBold', 'fonts/MYRIADPRO-SEMIBOLD.TTF'))
pdfmetrics.registerFont(TTFont('MyriadPro-Regular', 'fonts/MYRIADPRO-REGULAR.TTF'))


# Load config from file
config = configparser.ConfigParser()
config.read('config.ini')

# Get API endpoint and API token from config
api_endpoint = config['DEFAULT']['api_endpoint']
api_token = config['DEFAULT']['api_token']
issuer = config.get('Location', 'issuer')
issuer_bc = config.get('Location', 'issuer_bc')
issuer_ins = config.get('Location', 'issuer_ins')
issuer_dep = config.get('Location', 'issuer_dep')
no_email = config.get('DEFAULT', 'no_email')
aup_url = config.get('DEFAULT', 'aup_url')

class TextField(Flowable):
    def __init__(self, **options):
        Flowable.__init__(self)
        self.options = options
        # Use Reportlab's default size if not user provided
        self.width = options.get('width', 180)
        self.height = options.get('height', 18)

    def draw(self):
        self.canv.saveState()
        form = self.canv.acroForm
        form.textfieldRelative(**self.options)
        self.canv.restoreState()

        
class ChoiceField(Flowable):
    def __init__(self, **options):
        Flowable.__init__(self)
        options['relative'] = True
        self.options = options
        # Use Reportlab's default size if not user provided
        self.width = options.get('width', 80)
        self.height = options.get('height', 18)

    def draw(self):
        self.canv.saveState()
        form = self.canv.acroForm
        form.choice(**self.options)
        self.canv.restoreState()
        
class SignatureField(Flowable):
    def __init__(self, title='emp_sig', width=216, height=36, background_color=colors.HexColor("#D3D3D3")):
        super().__init__()
        self.title = title
        self.width = width
        self.height = height
        self.background_color = background_color
        self.coordinates = None  # Store the coordinates here
        self.page_number = None
        
    def draw(self):
        canvas = self.canv
        x, y = canvas.absolutePosition(0, 0)
        self.coordinates = (x, y, self.width, self.height)  # Save the coordinates
        self.page_number = self.canv.getPageNumber()
        canvas.setFillColor(self.background_color)
        canvas.rect(0, 0, self.width, self.height, fill=True)


class AuthorizationField(Flowable):
    def __init__(self, title='auth_sig', width=216, height=36, background_color=colors.HexColor("#D3D3D3")):
        super().__init__()
        self.title = title
        self.width = width
        self.height = height
        self.background_color = background_color
        self.coordinates = None  # Store the coordinates here
        self.page_number = None
    
    def draw(self):
        canvas = self.canv
        x, y = canvas.absolutePosition(0, 0)
        self.coordinates = (x, y, self.width, self.height)  # Save the coordinates
        self.page_number = self.canv.getPageNumber()
        canvas.setFillColor(self.background_color)
        canvas.rect(0, 0, self.width, self.height, fill=True)


pd.set_option('display.max_colwidth', 100)

user_chk = input("Enter user name, email, or ID (Leave empty for All Users): ")
user_chk = user_chk.strip()  # Remove leading/trailing whitespace

if not user_chk:
    user_chk = None  # Set user_chk to None if the input is empty
    
def getjson(resp_data):
    """Converts response data from binary to string or JSON format.
    
    Arguments:
        resp_data {string or Response} -- response data returned by requests api
    """
    if isinstance(resp_data, str):
        # input is already a string, no need to decode
        parsed = json.loads(resp_data)
    elif isinstance(resp_data, requests.Response):
        # input is a requests Response object, decode content and parse JSON
        parsed = json.loads(resp_data.content)
    else:
        raise ValueError("Invalid input type, must be string or Response")

    return parsed


def modify_pdf(pdf_filename, emp_sig, auth_sig):
    try:
        with open(pdf_filename, 'rb+') as doc:
            w = IncrementalPdfFileWriter(doc)
        
            # Define the position of the signature field
            sig_field_page = emp_sig.page_number - 1
            emp_sig_coordinates = emp_sig.coordinates
            box_coordinates = (
                emp_sig_coordinates[0],
                emp_sig_coordinates[1],
                emp_sig_coordinates[0] + emp_sig_coordinates[2],
                emp_sig_coordinates[1] + emp_sig_coordinates[3]
            )

            # Create the signature field specification
            sig_field_spec = SigFieldSpec(
                sig_field_name="Sig1",
                on_page=sig_field_page,
                box=box_coordinates
            )

            # Append the signature field
            append_signature_field(w, sig_field_spec)
            
            # Define the position of the signature field
            auth_field_page = auth_sig.page_number - 1 
            auth_sig_coordinates = auth_sig.coordinates
            box_coordinates2 = (
                auth_sig_coordinates[0],
                auth_sig_coordinates[1],
                auth_sig_coordinates[0] + auth_sig_coordinates[2],
                auth_sig_coordinates[1] + auth_sig_coordinates[3]
            )

            # Create the signature field specification
            auth_field_spec = SigFieldSpec(
                sig_field_name="Auth1",
                on_page=auth_field_page,
                box=box_coordinates2
            )

            # Append the signature field
            append_signature_field(w, auth_field_spec)

            w.write_in_place()
            print("Signature fields added successfully.")
    except Exception as e:
        print("Error:", str(e))




def generate_pdf(user_name, user_email, user_id, assetdf, accessories_df):
    doc = SimpleDocTemplate(
        f"{html.unescape(user_name)}_inventory.pdf", 
        pagesize=letter, 
        topMargin=18,  # Adjust the top margin as needed
        bottomMargin=18,
        leftMargin=24,
        rightMargin=24,
    )

        # Define styles
    styles = getSampleStyleSheet()
    header_style = styles['Heading1']
    header_style.fontName = 'MyriadPro-Bold'  # Set font explicitly
    paragraph_style = styles['BodyText']  # Paragraph style definition
    paragraph_style.fontName = 'MyriadPro-Regular'  # Set font explicitly
    url_style = styles['BodyText'].clone('URLStyle')
    url_style.textColor = 'blue'
    url_style.underline = True
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#041E42'),
        ('TEXTCOLOR', (0, 0), (-1, 0), '#FFFFFF'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'MyriadPro-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), '#EEEEEE'),
        ('FONTNAME', (0, 1), (-1, -1), 'MyriadPro-Regular'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    header_table = TableStyle([
        ('LEADING', (0, 2), (0, 6), 6),
        ('LEADING', (0, 7), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'MyriadPro-Regular'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 3), (0, 3), 6),
        ('FONTSIZE', (0, 5), (0, 5), 6),
        ('FONTSIZE', (0, 7), (0, 7), 6),
        ('FONTNAME', (0, 8), (0, 8), 'MyriadPro-Bold'),
        ('WORDWRAP', (0, 10), (0, 10), True),
    ])
    contact_table = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'MyriadPro-Regular'),
        ('WIDTH', (0, 0), (-1, -1), 'auto'),
    ])
    
    contact_table2 = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'MyriadPro-Regular'),
        ('WIDTH', (0, 0), (-1, -1), 'auto'),
    ])
 
    agree_table = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'MyriadPro-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('SPAN', (2, 0), (4, 0)),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'MyriadPro-Regular'),
        ('WIDTH', (0, 0), (-1, -1), 'auto'),
    ])
    
    agree_table2 = TableStyle([

        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'MyriadPro-Bold'),
        ('WIDTH', (0, 0), (-1, -1), 'auto'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 1), 7),
        ('LINEBELOW', (0, 0), (-1, 0), 4, colors.black),  # Add a line below the first row
        ('TOPPADDING', (0, 1), (-1, 1), 7),  # Add top padding to the second row
    ])

    # Create asset table data
    asset_data = [['Asset Status', 'Asset Tag', 'Asset Name', 'Asset Model', 'Serial #', 'Asset Condition']]
    for _, row in assetdf.iterrows():
        asset_data.append(list(row))

    # Create accessory table data
    accessory_data = [['Accessory Status', 'Accessory Name', 'Accessory ID', 'Accessory Condition']]
    for _, row in accessories_df.iterrows():
        accessory_data.append(list(row))

    # Create asset table
    asset_table = Table(asset_data, repeatRows=1)
    asset_table.setStyle(table_style)

    # Create accessory table
    accessory_table = Table(accessory_data, repeatRows=1)
    accessory_table.setStyle(table_style)
    
    #Header Table
    header_data = [
        [issuer],
        [issuer_bc],
        [TextField(name='Name of lending issuer Instutution', tooltip='Enter the Name of lending issuer instutution', value=issuer_ins, width=200, height=16)],
        ['Name of lending issuer Instutution'],
        [TextField(name='Name of lending issuer Department', tooltip='Enter the Name of lending issuer department', value=issuer_dep, width=90, height=16)],
        ['Name of issuer Lending Department'],
        [TextField(name='Name of lending issuer Employee', tooltip='Enter the Name of lending issuer Employee', value=html.unescape(user_name), width=200, height=16)],
        ['Name of issuer Employee'],
        ['Equipment Loan Agreement'],
    ]
    header = Table(header_data)
    header.setStyle(header_table)
         
    #Agreement table
        # Add URL link

    contact_data= [
        ['issuer Employee Name:', TextField(name='employee_name', tooltip='Enter the Name of lending issuer Employee', value=html.unescape(user_name), width=200, height=16), '', 'Telephone:', TextField(name='Telephone', tooltip='Name of issuer Employee Telephone', value='775-784-6265', width=90, height=18), ''],
    ]
    contact_data2= [
        ['Employee Campus Address:', ChoiceField(name='address', tooltip='Primary Equipment Address', value='NJC 109', options=['NJC 109', 'WRB 1001', 'EJC 239', 'Off Site', 'Hybrid'], width=80, height=18), '', f"{issuer_dep} Email:", TextField(name='Email', tooltip='Name of issuer Employee email', value=user_email, width=200, height=18)],
    ]   
    contact = Table(contact_data)
    contact.setStyle(contact_table)
    contact2 = Table(contact_data2)
    contact2.setStyle(contact_table2)
   
    agree_deny = ChoiceField(name='CASAT_AUP', tooltip='AUP Select', value='Accept', options=['Accept', 'Deny'], width=60, height=14)
    url_link = f'<a href="{aup_url}"><u>Casat Acceptable Use Policy</u></a>'

    signature = []
    authorization = []
    emp_sig = SignatureField()
    signature.append(emp_sig)
    auth_sig = AuthorizationField()
    authorization.append(auth_sig)
    agree_data = [
        ['Please read and accept the CASAT Acceptable Use Policy:', agree_deny, Paragraph(url_link, url_style), '', ''],
    ]
    agree_data2 = [
        ['Digital Signature:', emp_sig, '', ''],
        ['Approved by:', auth_sig, '', ''],
    ]
    agree = Table(agree_data)
    agree.setStyle(agree_table)
    agree2 = Table(agree_data2)
    agree2.setStyle(agree_table2)
    


    # Create the story
    story = []
    
    story.append(header)
    story.append(Paragraph('The undersigned hereby acknowledges receipt of the equipment listed below, to be in good condition, except as otherwise noted. Nevada System of Higher Education (issuer) employee may be held responsible for damage or loss of loaned equipment.'))
    story.append(Paragraph("Assets:", header_style))
    story.append(asset_table)
    story.append(Paragraph("Accessories:", header_style))
    story.append(accessory_table)
    story.append(contact)
    story.append(contact2)
    story.append(agree)
    story.append(agree2)
    story.append(Paragraph(f"Asset User ID: {user_id}", paragraph_style))

            


    # Build the PDF
    doc.build(story)
        # Retrieve the coordinates


    pdf_filename = f"{html.unescape(user_name)}_inventory.pdf"
    print(f"PDF {user_name}_inventory.pdf created successfully")

    modify_pdf(pdf_filename, emp_sig, auth_sig)


def get_users_stock(user_chk=None):
    headers = {'Authorization': f'Bearer {api_token}'}
    users = requests.get(api_endpoint + '/users/', headers=headers)
    jsondata = getjson(users)

    users_jsondata = jsondata["rows"]
    users_df = pd.DataFrame(users_jsondata, columns=['id', 'name', 'email'])
    
    if user_chk is not None and user_chk != "":
        # Check if user_chk can be converted to an integer
        if str(user_chk).isdigit():
            user_chk = int(user_chk)  # Convert user_chk to integer
        
        # Filter the DataFrame to get only the row that contains the user_chk value
        users_df = users_df[users_df['id'].isin([user_chk]) | users_df['name'].isin([user_chk]) | users_df['email'].isin([user_chk])]
        
        print(users_df)
        
    for index, user in users_df.iterrows():
        user_id = user['id']
        user_name = user['name']
        user_email = user['email']
        if pd.isnull(user_email) or user_email.strip() == "":
            user_email = no_email
        user_assets = requests.get(api_endpoint + f'/users/{user_id}/assets', headers=headers)
        asset_list = []
        
        try:
            json_assets = getjson(user_assets)

            if "rows" in json_assets:
                asset_jsondata = json_assets["rows"]
                for asset in asset_jsondata:
                    asset_tag = asset['asset_tag']
                    asset_name = asset['name']
                    asset_model = asset['model']['name']  # Extract the model name from the dictionary
                    asset_model = html.unescape(asset_model)  # Decode HTML entities
                    asset_serial = asset['serial']
                    asset_name = html.unescape(asset_name)  # Decode HTML entities
                    asset_status = ChoiceField(name=f'Asset Status {asset_tag}', tooltip='Status', value='Present', options=['', 'Present', 'Missing', 'Returned', 'Other'], width=80, height=14)
                    asset_condition = ChoiceField(name=f'Asset Condition {asset_tag}', tooltip='Condition', value='Good', options=['New', 'Good', 'Fair', 'Poor', 'Other'], width=80, height=14)
                    asset_list.append([asset_status, asset_tag, asset_name, asset_model, asset_serial, asset_condition])
                assetdf = pd.DataFrame(asset_list, columns=['Asset Status', 'Asset Tag', 'Asset Name', 'Asset Model', 'Serial #', 'Condition'])
                if assetdf.empty:
                    asset_list.append(['', 'No Assets Assigned', '', '', '', ''])
                    assetdf = pd.DataFrame(asset_list, columns=['Asset Status', 'Asset Tag', 'Asset Name', 'Asset Model', 'Serial #', 'Condition'])
                    print("No assets found for this user")
                else:
                    print("Assets found for this user")
                    
            else:
                asset_list.append(['', 'Error in data set', '', '', '', ''])
                assetdf = pd.DataFrame(asset_list, columns=['Asset Status', 'Asset Tag', 'Asset Name', 'Asset Model', 'Serial #', 'Condition'])
                print("No assets found in the asset data set")
        except Exception as e:
            asset_list.append(['', 'Error in data set', '', '', '', ''])
            assetdf = pd.DataFrame(asset_list, columns=['Asset Status', 'Asset Tag', 'Asset Name', 'Asset Model', 'Serial #', 'Condition'])
            print(f"An error occurred while retrieving assets: {str(e)}")

        user_accessories = requests.get(api_endpoint + f'/users/{user_id}/accessories', headers=headers)
        accessory_list = []
        try:
            json_acc = getjson(user_accessories)
            if "rows" in json_acc:
                accessory_jsondata = json_acc["rows"]
                # Inside the get_users_stock function, when creating the choice field for accessories
                accessory_count = {}
                for accessory in accessory_jsondata:
                    accessory_id = accessory['id']
                    accessory_name = accessory['name']
                    accessory_name = html.unescape(accessory_name)  # Decode HTML entities

                    # Check if the accessory_id is already in the accessory_count dictionary
                    if accessory_id in accessory_count:
                        # Increment the count for the accessory_id
                        accessory_count[accessory_id] += 1
                        # Append the tick-up number to the accessory_id
                        choice_field_name = f'Accessory Status {accessory_id}_{accessory_count[accessory_id]}'
                        accessory_condition_field = f'Accessory Condition {accessory_id}_{accessory_count[accessory_id]}'
                    else:
                        # First occurrence of the accessory_id, no tick-up number needed
                        accessory_count[accessory_id] = 1
                        choice_field_name = f'Accessory Status {accessory_id}'
                        accessory_condition_field = f'Accessory Condition {accessory_id}'
                        
                    accessory_status = ChoiceField(name= choice_field_name, tooltip='Status', value='Present', options=['', 'Present', 'Missing', 'Returned', 'Other'], width=80, height=14)
                    accessory_condition = ChoiceField(name= accessory_condition_field, tooltip='Accessory Condition', value='Good', options=['New', 'Good', 'Fair', 'Poor', 'Other'], width=80, height=14)
                    accessory_list.append([accessory_status, accessory_name, accessory_id, accessory_condition])
                    accessories_df = pd.DataFrame(accessory_list, columns=['Accessory Status', 'Accessory Name', 'Accessory ID', 'Condition'])

                if accessories_df.empty:
                    accessory_list.append(['','No Accessories Assigned to user', '',''])
                    accessories_df = pd.DataFrame(accessory_list, columns=['Accessory Status', 'Accessory Name', 'Accessory ID', 'Condition'])
                    print("No accessories found for this user")
                else:
                    print("Accessories found for this user")
                    
            else:
                accessory_list.append(['', 'Error in data set', '', ''])
                accessories_df = pd.DataFrame(accessory_list, columns=['Accessory Status', 'Accessory Name', 'Accessory ID', 'Condition'])
                print("No accessories found in the accessory data")
        except Exception as f:
            accessory_list.append(['', 'Error in data set', '', ''])
            accessories_df = pd.DataFrame(accessory_list, columns=['Accessory Status', 'Accessory Name', 'Accessory ID', 'Condition'])
            print(f"An error occurred while retrieving accessories: {str(f)}")
        generate_pdf(user_name, user_email, user_id, assetdf, accessories_df)
        print('=========================================================================================================')

get_users_stock(user_chk)
