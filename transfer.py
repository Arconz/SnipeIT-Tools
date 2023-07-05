import requests
import pandas as pd
import configparser
import json
import html

# Load config from file
config = configparser.ConfigParser()
config.read('config.ini')

# Get API endpoint and API token from config
api_endpoint = config['DEFAULT']['api_endpoint']
api_token = config['DEFAULT']['api_token']

# Set the maximum column width
pd.set_option('display.max_colwidth', 100)

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
user_1 = input("Enter sender's name , email, or ID: ")
user_1 = user_1.strip()  # Remove leading/trailing whitespace

user_2 = input("Enter receiver's name, email, or ID: ")
user_2 = user_2.strip()  # Remove leading/trailing whitespace


def get_users_stock(user_1, user_2):
    headers = {'Authorization': f'Bearer {api_token}'}
    users = requests.get(api_endpoint + '/users/', headers=headers)
    jsondata = getjson(users)

    users_jsondata = jsondata["rows"]
    users_df = pd.DataFrame(users_jsondata, columns=['id', 'name', 'email'])

    if str(user_1).isdigit():
            user_1 = int(user_1)  # Convert user_chk to integer
        
    # Filter the DataFrame to get only the row that contains the user_chk value
    sender = users_df[users_df['id'].isin([user_1]) | users_df['name'].isin([user_1]) | users_df['email'].isin([user_1])]
    sender_name = sender.iloc[0]['name']  # Access the name value of the first row
    print(f"Move accessories from {sender_name}")

    if str(user_2).isdigit():
            user_2 = int(user_2)  # Convert user_chk to integer
        
    # Filter the DataFrame to get only the row that contains the user_chk value
    receiver = users_df[users_df['id'].isin([user_2]) | users_df['name'].isin([user_2]) | users_df['email'].isin([user_2])]
    for index, user in receiver.iterrows():
        receiver_id = user['id']
        receiver_name = user['name']     
    print(f"To: {receiver_name}")

    confirm = input("Is this correct? (Type 'y' for yes or any other input to exit): ")
    if confirm.lower() in ['y', 'yes']:
        # Continue with further processing or actions
        # ...
        pass
    else:
        print("Exiting...")
        exit()

    for index, user in sender.iterrows():
        user_id = user['id']
        user_name = user['name']
        user_email = user['email']
        print(f"User Name: {html.unescape(user_name)}, User Email: {user_email}, User ID: {user_id}")
        print('---------------------------------------------------------------------------------------------------------')
        
        user_assets = requests.get(api_endpoint + f'/users/{user_id}/assets', headers=headers)

        try:
            json_assets = getjson(user_assets)

            if "rows" in json_assets:
                asset_jsondata = json_assets["rows"]
                asset_list = []
                for asset in asset_jsondata:
                    asset_tag = asset['asset_tag']
                    asset_name = asset['name']
                    asset_model = asset['model']['name']  # Extract the model name from the dictionary
                    asset_model = html.unescape(asset_model) #Decode HTML entities
                    asset_serial = asset['serial']
                    asset_name = html.unescape(asset_name)  # Decode HTML entities
                    asset_list.append([asset_tag, asset_name, asset_model, asset_serial])
                assetdf = pd.DataFrame(asset_list, columns=['Asset Tag', 'Asset Name', 'Asset Model', 'Serial #'])
                if assetdf.empty:
                    print("No assets found for this user")
                else:
                    print(assetdf)
            else:
                print("No assets found in the asset data set")           
        except Exception as e:                
            print(f"An error occurred: {str(e)}")
        
        print('---------------------------------------------------------------------------------------------------------')

        user_accessories = requests.get(api_endpoint + f'/users/{user_id}/accessories', headers=headers)

        try:
            json_acc = getjson(user_accessories)
            if "rows" in json_acc:
                accessory_jsondata = json_acc["rows"]
                accessory_list = []
                for accessory in accessory_jsondata:
                    accessory_id = accessory['id']
                    accessory_name = accessory['name']
                    accessory_name = html.unescape(accessory_name)  # Decode HTML entities
                    accessory_list.append([accessory_name, accessory_id])
                    acc_test = requests.get(api_endpoint + f'/accessories/{accessory_id}/checkedout', headers=headers)
                    json_acc_test = getjson(acc_test)
                    checked_out_user = json_acc_test['rows']
                    # Filter the dictionaries to get only the entry that contains the user_id
                    filtered_checked_out_user = [user for user in checked_out_user if user['id'] == user_id]

                    if filtered_checked_out_user:
                        chkd_out = filtered_checked_out_user[0]  # Assuming there is only one matching entry
                        assigned_pivot_id = chkd_out['assigned_pivot_id']
                        print(f"Assigned Pivot ID: {assigned_pivot_id}")
                        checkin = requests.post(api_endpoint + f'/accessories/{assigned_pivot_id}/checkin', headers=headers)
                        payload = {"assigned_to": receiver_id}
                        print(checkin.text)
                        checkout = requests.post(api_endpoint + f'/accessories/{accessory_id}/checkout', json=payload, headers=headers)
                        print(checkout.text)
                    else:
                        print("No checked out entries found for this user")
                        
                accessories_df = pd.DataFrame(accessory_list, columns=['Accessory Name', 'Accessory ID'])
                
                if accessories_df.empty:
                    print("No accessories found for this user")
                else:

                    print(accessories_df)
            else:
                print("No accessories found in the accessory data")
        except Exception as f:
            print(f"An error occurred: {str(f)}")
            
        print('=========================================================================================================')

get_users_stock(user_1, user_2)

