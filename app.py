from flask import Flask, render_template
from flask import request
import sqlite3
app = Flask(__name__)

def film_dictionary(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class db_connection:
    def __init__(self):
        self.conn = sqlite3.connect('database.db')
        self.conn.row_factory = film_dictionary
        self.cur = self.conn.cursor()

    def __enter__(self):
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()


def get_db_result(query):
    conn = sqlite3.connect('database.db')
    conn.row_factory = film_dictionary
    cur = conn.cursor()
    res = cur.execute(query)
    result = res.fetchall()
    conn.close()
    return result


@app.route('/')
def main_page():  # put application's code here
    with db_connection() as cur:
       result = cur.execute("SELECT * FROM film order by added_at desc limit 10").fetchall()

    # result = get_db_result('SELECT id, poster, name FROM film order by added_at desc limit 10')
    return result

@app.route('/register', methods=['GET'])
def register_page():
    return """
    <form action="/register" method="post">
    
    <label for="fname">First name:</label><br>
    <input type="text" id="fname" name="fname"><br>
    
    <label for="lname">Last name:</label><br>
    <input type="text" id="lname" name="lname"><br>
    
    <label for="password">Password:</label><br>
    <input type="password" id="password" name="password"><br>
    
    <label for="login">Login:</label><br>
    <input type="text" id="login" name="login"><br>
    
    <label for="email">Email:</label><br>
    <input type="email" id="email" name="email"><br>
    
    <label for="birth_day">Birth date:</label><br>
    <input type="date" id="birth_day" name="birth_date"><br>
    
    
    <input type="submit" value="Submit">
    </form>
    """


@app.route('/register', methods=['POST'])
def user_register():
    first_name = request.form['fname']
    last_name = request.form['lname']
    password = request.form['password']
    login = request.form['login']
    email = request.form['email']
    birth_date = request.form['birth_date']
    with db_connection() as cur:
        cur.execute('INSERT INTO user (first_name, last_name, password, login, email, birth_date) VALUES (?, ?, ?, ?, ?, ?)',
                    (first_name, last_name, password, login, email, birth_date))
    return 'Register'

@app.post('/login')
def user_login():
    return 'Login'

@app.route('/logout', methods=['GET'])
def user_logout():
    return 'Logout'

@app.route('/user/<user_id>', methods=['GET', 'PATCH'])
def user_profile(user_id):
    return f'User {user_id}'

@app.route('/user/<user_id>', methods=['DELETE'])
def user_delete(user_id):
    return f'User {user_id} delete'

@app.route('/films', methods=['GET'])
def films():
    result = get_db_result('SELECT id, poster, name FROM film order by added_at desc')
    return result

@app.route('/films', methods=['POST'])
def film_add():
    return 'Film added'

@app.route('/films/<film_id>', methods=['GET'])
def film_info(film_id):
    with db_connection() as cur:
        result = cur.execute(f"SELECT * FROM film where id={film_id}").fetchall()
        actors = cur.execute(f"SELECT * FROM actor join actor_film on actor.id == actor_film.actor_id where actor_film.film_id={film_id}").fetchall()
        genres = get_db_result(f"SELECT * FROM genre_film where film_id={film_id}").fetchall()


    # result = get_db_result(f"SELECT * FROM film where id={film_id}")
    # actors = get_db_result(f"SELECT * FROM actor join actor_film on actor.id == actor_film.actor_id where actor_film.film_id={film_id}")
    # genres = get_db_result(f"SELECT * FROM genre_film where film_id={film_id}")
    return f'Film {film_id} is {result}, actors: {actors}, genres: {genres}'

@app.route('/films/<film_id>', methods=['PUT'])
def film_update(film_id):
    return f'Film {film_id} updated'


@app.route('/films/<film_id>', methods=['DELETE'])
def film_delete(film_id):
    return f'Film {film_id} deleted'


@app.route('/films/<film_id>/rating', methods=['POST'])
def film_rating(film_id):
    return f"Film {film_id} rated"

@app.route('/films/<film_id>/rating', methods=['GET'])
def film_rating_info(film_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    res = cur.execute(f"SELECT rating FROM film where id={film_id}")
    result = res.fetchone()
    return f'Film {film_id} have rating {result}'

@app.route('/films/<film_id>/rating/<feedback_id>', methods=['DELETE'])
def film_rating_delete(film_id, feedback_id):
    return f'Film {film_id} rating {feedback_id} deleted'

@app.route('/films/<film_id>/rating/<feedback_id>', methods=['PUT'])
def film_rating_update(film_id, feedback_id):
    return f'Film {film_id} rating {feedback_id} updated'

@app.route('/films/<film_id>/rating/<feedback_id>/feedback', methods=['GET'])
def film_rating_feedback(film_id, feedback_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    res = cur.execute(f"SELECT description, grade FROM feedback where film ={film_id} and id={feedback_id}")
    result = res.fetchone()
    return f'Film have {result}: {film_id} rating {feedback_id} feedback'

@app.route('/users/<user_id>/list', methods=['GET', 'POST'])
def user_list(user_id):
    return f'User {user_id} list'

@app.route('/users/<user_id>/list', methods=['DELETE'])
def user_list_delete(user_id):
    return f'User {user_id} list deleted'

@app.route('/users/<user_id>/list/<list_id>', methods=['GET', 'POST'])
def user_list_item(user_id, list_id):
    return f'User {user_id} list item {list_id}'


@app.route('/users/<user_id>/list/<list_id>/<film_id>', methods=['DELETE'])
def user_list_item_delete(user_id, list_id, film_id):
    return f'User {user_id} list item {list_id} deleted'

@app.get('/login')
def login_pages():
    return render_template('login.html')

@app.post('/login')
def users_login():
    return 'Login'

@app.get('/logout')
def users_logout():
    return 'Logout'

@app.get('/registration')
def register_pages():
    return render_template('register.html')

@app.post('/register')
def users_register():
    return 'Register'


if __name__ == '__main__':
    app.run()

