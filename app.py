import functools
import os
from dateutil import parser
from sqlalchemy import select
import database
from click import password_option
from flask import Flask, render_template, redirect, url_for
from flask import request, session
import sqlite3
import models

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

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


def decorator_check_login(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'logged_in' in session:
            return func(*args, **kwargs)
        else:
            return redirect(url_for('user_login'))
    return wrapper

@app.route('/')
@decorator_check_login
def main_page():  # put application's code here
    with db_connection() as cur:
       result = cur.execute("SELECT * FROM film order by added_at desc limit 10").fetchall()

    # result = get_db_result('SELECT id, poster, name FROM film order by added_at desc limit 10')
    for one_film in result:
        print(one_film['name'])
        print(one_film['year'])
        print(one_film['rating'])
    return render_template('main.html', films=result)

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def user_register():
    first_name = request.form['fname']
    last_name = request.form['lname']
    password = request.form['password']
    login = request.form['login']
    email = request.form['email']
    birth_date = parser.parse(request.form['birth_date'])

    database.init_db()

    new_user = models.User(first_name=first_name, last_name=last_name, password=password, login=login, email=email, birth_date=birth_date)

    database.db_session.add(new_user)
    database.db_session.commit()

    return 'Register'

@app.route('/login', methods=['GET'])
def user_login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def user_login_post():
    login = request.form['login']
    password = request.form['password']


    database.init_db()

    stmt = select(models.User).where(models.User.login == login, models.User.password == password)
    data = database.db_session.execute(stmt).fetchall()
    if data:
        user_obj = data[0][0]


    result = database.db_session.query(models.User).filter_by(login=login, password=password).first()
    # result == user_obj

    if result:
        session['logged_in'] = True
        session['user_id'] = result.id
        return f'Login with user {result}'
    return 'Login failed'

@app.route('/logout', methods=['GET'])
@decorator_check_login
def user_logout():
    session.clear()
    return 'Logout'

@app.route('/user/<user_id>', methods=['GET', 'POST'])
def user_profile(user_id):
    session_user_id = session.get('user_id')
    if request.method =='POST':
        if int(user_id) != session_user_id:
            return 'You can edit only your profile'

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        birth_date = request.form['birth_date']
        phone = request.form['phone']
        photo = request.form['photo']
        password = request.form['password']
        additional_info = request.form['additional_info']
        with db_connection() as cur:
            cur.execute(f"UPDATE user SET first_name='{first_name}', last_name='{last_name}', email='{email}', birth_date='{birth_date}', phone_number='{phone}', photo='{photo}', password='{password}', additional_info='{additional_info}' WHERE id={user_id}")
        return f'User {user_id} updated'
    else:
        with db_connection() as cur:
            cur.execute(f'SELECT * FROM user WHERE id={user_id}')
            user_by_id = cur.fetchone()

            if session_user_id is None:
                user_by_session = 'No user in session'
            else:
                cur.execute(f'SELECT * FROM user WHERE id={session_user_id}')
                user_by_session = cur.fetchone()
        return render_template('user_page.html', user=user_by_id, user_session=user_by_session)



@app.route('/user/<user_id>/delete', methods=['GET'])
def user_delete(user_id):
    session_user_id = session.get('user_id')
    if user_id == session_user_id:
        return f'User {user_id} delete'
    else:
        return 'You can delete only your profile'

@app.route('/films', methods=['GET']) # /films?name=fhuf&year=2024&country=Ukraine -> select * from film where name like '%fhuf%' and year=2024 and country=Ukraine
def films():
    filter_params = request.args
    filter_list_text = []

    special_keys = {'actor', 'genre'}

    for key, value in filter_params.items():
        if value:

            if key in special_keys:
                continue

            if key == 'name':
                filter_list_text.append(f"name like'%{value}%'")
            else:
                filter_list_text.append(f"{key}='{value}'")

    joins = []

    genre = filter_params.get('genre')
    actor = filter_params.get('actor')

    if genre:
        joins.append("JOIN genre_film ON genre_film.film_id = film.id")
        filter_list_text.append(f"genre_film.genre_id='{genre}'")

    if actor:
        joins.append("JOIN actor_film ON actor_film.film_id = film.id")
        joins.append("JOIN actor ON actor.id = actor_film.actor.actor_id")
        filter_list_text.append(
            f"(actor.first_name like '%{actor}%' OR actor.last_name like '%{actor}%')"
        )

    additional_filter = ""
    if filter_params:
        additional_filter = "where " + " and ".join(filter_list_text)

    join_part = " ".join(joins)
    if joins:
        result = get_db_result(f"SELECT DISTINCT film.* FROM film {join_part} {additional_filter} order by film.added_at desc")
    else:
        result = get_db_result(f'SELECT * FROM film {additional_filter} order by film.added_at desc')
    genres = get_db_result("SELECT * FROM genre")
    countries = get_db_result("SELECT * FROM country")
    return render_template('films.html', films=result, countries=countries, genres=genres)

@app.route('/films', methods=['POST'])
def film_add():
    return 'Film added'

@app.route('/films/<film_id>', methods=['GET'])
def film_info(film_id):
    with db_connection() as cur:
        result = cur.execute(f"SELECT * FROM film where id={film_id}").fetchall()
        actors = cur.execute(f"SELECT * FROM actor join actor_film on actor.id == actor_film.actor_id where actor_film.film_id={film_id}").fetchall()
        genres = get_db_result(f"SELECT * FROM genre_film where film_id={film_id}")

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

