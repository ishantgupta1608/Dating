from flask import *
from azure.storage.blob import *
import io, uuid, pickle
import requests
from PIL import Image
from base64 import b64encode
 
print('hi')
connect_str = open('string.txt', 'r').read().rstrip()
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
accounts_client = blob_service_client.get_container_client('datingaccounts')
profiles_client = blob_service_client.get_container_client('datingprofiles')
sessions_client = blob_service_client.get_container_client('datingsessions')
likes_client = blob_service_client.get_container_client('datinglikes')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

@app.route('/')
def my_profile():
    if 'uid' not in session:
        return redirect('/login')
    uid = session['uid']
    username = sessions_client.download_blob(uid).readall().decode('utf-8')
    profile = pickle.loads(profiles_client.download_blob(username).readall())
    return render_template('my_profile.html', name = profile['name'], age = profile['age'], city = profile['city'], photo = profile['photo'])


@app.route('/update_profile', methods = ['POST'])
def update_profile():
    if 'uid' not in session:
        return redirect('/login')
    uid = session['uid']
    username = sessions_client.download_blob(uid).readall().decode('utf-8')
    if not request.files.get('photo', None):
        photo_bytes = pickle.loads(profiles_client.download_blob(username).readall())['photo']
    else:
        photo_bytes = b64encode(request.files['photo'].read()).decode('utf-8')
    new_profile = {'name' : request.form['name'], 'age' : request.form['age'], 'city' : request.form['city'], 'photo' : photo_bytes}
    profiles_client.delete_blob(username)
    profiles_client.upload_blob(username, pickle.dumps(new_profile))
    return redirect('/')
    
@app.route('/show_profiles')
def show_profiles():
    if 'uid' not in session:
        return redirect('/login')
    uid = session['uid']
    username = sessions_client.download_blob(uid).readall().decode('utf-8')
    usernames_list = [a.name for a in accounts_client.list_blobs()]
    usernames_list.remove(username)
    likes_list = pickle.loads(likes_client.download_blob(username).readall())
    html = """
    <a href = '/'> <h3> My Profile </h3> </a>
    <br/>
    <h2> <font color = 'red'> Red profiles matched with you! </font> </h2>
    <form action = '/update_likes' method = 'post'> <br/>"""
    for uname in usernames_list:
        profile_dict = pickle.loads(profiles_client.download_blob(uname).readall())
        i_like_them = uname in likes_list
        checked = ""
        if i_like_them:
            checked = "checked"
        they_like_me = username in pickle.loads(likes_client.download_blob(uname).readall())
        color = 'black'
        if i_like_them and they_like_me:
            color = 'red'
        html = html + "Name : " + profile_dict['name'] + ", Age : " + str(profile_dict['age']) + ", City : " + profile_dict['city'] + "&nbsp; <img src = 'data:;base64,{}' width = 100 height = 100> ".format(profile_dict['photo'])
        html = html + "<input type = 'checkbox' name = {} {}> <font color = '{}'> Check to Like Profile </font> <br/>".format(uname, checked, color)
    html = html + "<br/> <input type = 'submit' value = 'Update'> </form>"
    return html

@app.route('/update_likes', methods = ['POST'])
def update_likes():
    if 'uid' not in session:
        return redirect('/login')
    uid = session['uid']
    username = sessions_client.download_blob(uid).readall().decode('utf-8')
    likes = []
    for uname in request.form:
        likes.append(uname)
    likes_client.delete_blob(username)
    likes_client.upload_blob(name = username, data = pickle.dumps(likes))
    return redirect('/show_profiles')

@app.route('/bye')
def bye():
    session.clear()
    print(session)
    if 'uid' not in session:
        print('abcd')
        return redirect('/login')
    uid = session['uid']
    username = sessions_client.download_blob(uid).readall().decode('utf-8')
    session.clear()
    return 'Bye' + username
    
    
@app.route('/sign_up')
def sign_up():
    return render_template('sign_up.html')

@app.route('/save_account', methods = ['POST'])
def save_account():
    username = request.form['username']
    password = request.form['password']
    if username.isspace() or password.isspace() or username == '' or password == '': 
        html = """
        Username or password can not be blank <br/>
        <a href = '/sign_up'> Try again </a>
        """
        return html
    usernames_list = [a.name for a in accounts_client.list_blobs()]
    if username in usernames_list:
        html = """
        Username taken <br/>
        <a href = '/sign_up'> Try again </a>
        """
        return html
    accounts_client.upload_blob(name = username, data = io.BytesIO(password.encode('utf-8')))
    photo_bytes = b64encode(io.BytesIO(requests.get("https://www.argentum.org/wp-content/uploads/2018/12/blank-profile-picture-973460_6404.png").content).read()).decode('utf-8')
    profile_dict = {'name' : '', 'age' : 0, 'city' : '', 'photo' : photo_bytes}
    profiles_client.upload_blob(name = username, data = pickle.dumps(profile_dict))
    likes_client.upload_blob(name = username, data = pickle.dumps([]))
    html = """
    Account created <br/>
    <a href = '/login'> Login </a>
    """    
    return html

@app.route('/login')
def login():
    return render_template('login.html')
    
@app.route('/create_session', methods = ['POST'])
def create_session():
    username = request.form['username']
    password = request.form['password']
    usernames_list = [a.name for a in accounts_client.list_blobs()]
    if username in usernames_list:
        if password == accounts_client.download_blob(username).readall().decode('utf-8'):
            uid = str(uuid.uuid4())
            session['uid'] = uid
            sessions_client.upload_blob(name = uid, data = io.BytesIO(username.encode('utf-8')))
            return redirect('/')
    html = """ 
    Username or password incorrect <br/>
    <a href = '/login'> Try again </a>
    """
    return html           

if __name__ == '__main__':
    app.run()
