import os
import functools
import secrets
import random
import string

from celery.worker.control import active

import database
import email_worker
import models
from dateutil import parser
from flask import Flask, render_template, redirect, url_for, jsonify
from flask import request, session
from sqlalchemy import select, update, func, delete


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def check_user_allowance(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user_id_from_endpoint= request.view_args['user_id']
        user_id_from_session = session.get("user_id")
        if user_id_from_endpoint != user_id_from_session:
            raise Exception("Unauthorized")
        return func(*args, **kwargs)
    return wrapper


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
    database.init_db()
    smth = select(models.Film).limit(10).order_by(models.Film.added_at.desc())
    data = database.db_session.execute(smth).fetchall()
    data2 = [itm[0] for itm in data]
    return render_template('main.html', films=data2)


@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

CONFIRMATIONS = {}

def create_and_save_confirmation(user_id, email):
    code = secrets.token_hex(4)
    CONFIRMATIONS[email] = {"code": code, "user_id": user_id}
    return code

def build_message_body_for_confirmation(code, user_first_name):
    return f""" Hi {user_first_name}! Your confirmation code: {code}"""

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
    new_user.active = False
    database.db_session.add(new_user)
    database.db_session.flush()

    secret_code = create_and_save_confirmation(new_user.id, new_user.email)
    message_body = build_message_body_for_confirmation(secret_code, user_first_name=new_user.first_name)
    email_worker.send_email.delay("Confirm your email", message_body, new_user.email)
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

    # v2
    # stmt = select(models.User).where(models.User.login == login, models.User.password == password)
    # data = database.db_session.execute(stmt).fetchall()
    # if data:
    #     user_obj = data[0][0]


    result = database.db_session.query(models.User).filter_by(login=login, password=password).first()
    # result == user_obj

    if result:
        session['logged_in'] = True
        session['user_id'] = result.id
        return f'Login with user {result}'
    return 'Login failed'

@app.route('/confirm', methods=['POST'])
def confirm_email():
    code = request.form["code"]
    email = request.form["email"]

    record = CONFIRMATIONS.get(email)
    if not record:
        return "Without confirmation request for this email", 400

    if code != record["code"]:
        return "Wrong code", 400

    database.init_db()
    stmt = (
        update(models.User)
        .where(models.User.id == record["user_id"])
        .values(active=True)
    )

    database.db_session.execute(stmt)
    database.db_session.commit()

    del CONFIRMATIONS[email]

    return "Confirmed"

@app.route('/logout', methods=['GET'])
@decorator_check_login
def user_logout():
    session.clear()
    return 'Logout'

@app.route('/user/<user_id>', methods=['GET', 'POST'])
def user_profile(user_id):

    database.init_db()
    session_user_id = session.get('user_id')
    if request.method =='POST':
        if int(user_id) != session_user_id:
            return 'You can edit only your profile'

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        birth_date = parser.parse(request.form['birth_date'])
        phone = request.form['phone']
        photo = request.form['photo']
        password = request.form['password']
        additional_info = request.form['additional_info']

        stmt = update(models.User).where(models.User.id == user_id).values(first_name=first_name, last_name=last_name, email=email, password=password, birth_date=birth_date, phone_number=phone, photo=photo, additional_info=additional_info)
        database.db_session.execute(stmt)
        database.db_session.commit()
        return f'User {user_id} updated'

    else:

        query_user_by_id = select(models.User).where(models.User.id == user_id)
        user_by_id = database.db_session.execute(query_user_by_id).scalar_one()

        if session_user_id is None:
            user_by_session = 'No user in session'
        else:
            query_user_by_session = select(models.User).where(models.User.id == session_user_id)
            user_by_session = database.db_session.execute(query_user_by_session).scalar_one()

        database.db_session.commit()
    return render_template('user_page.html', user=user_by_id, user_session=user_by_session)



@app.route('/user/<user_id>/delete', methods=['GET'])
def user_delete(user_id):
    session_user_id = session.get('user_id')
    if int(user_id) == session_user_id:
        database.init_db()
        stmt = delete(models.User).where(models.User.id == user_id)
        database.db_session.execute(stmt)
        database.db_session.commit()
        database.db_session.close()
        return f'User {user_id} delete'
    else:
        return 'You can delete only your profile'

@app.route('/films', methods=['GET'])
@decorator_check_login
def films():
    filter_params = request.args
    films_query = select(models.Film)

    for key, value in filter_params.items():
        if value:
            if key == 'name':
                films_query = films_query.where(models.Film.name.like(f"%{value}%"))
            else:
                if key == 'rating':
                    value = float(value)
                    films_query = films_query.where(models.Film.rating == value)
                if key == 'country':
                    films_query = films_query.where(models.Film.country == value)
                if key == 'year':
                    films_query = films_query.where(models.Film.year == int(value))
                if key == 'genre':
                    films_query = films_query.join(models.GenreFilm, models.GenreFilm.film_id == models.Film.id) \
                        .join(models.Genre, models.Genre.genre == models.GenreFilm.genre_id) \
                        .where(models.Genre.genre == value )


    films = films_query.order_by(models.Film.added_at.desc())
    result_films = database.db_session.execute(films).scalars()
    countries = select(models.Country)
    result_countries = database.db_session.execute(countries).scalars()

    return render_template("films.html", films=result_films, countries=result_countries)


@app.route('/films', methods=['POST'])
def film_add():
    database.init_db()


    data = request.get_json() or {}
    name = data.get('name')
    poster = data.get('poster')
    description = data.get('description')
    rating = data.get('rating')
    country = data.get('country')
    year = data.get("year")
    duration = data.get("duration")

    if not name:
        return jsonify({"error": "name is required"}), 400

    new_film = models.Film(
        name=name,
        poster=poster,
        description=description,
        rating=rating,
        country=country,
        year=year,
        duration=duration
    )

    database.db_session.add(new_film)
    database.db_session.commit()

    return redirect(url_for(f"/films/{new_film.id}"))

@app.route('/films/<int:film_id>', methods=['GET'])
def films_info(film_id):
    database.init_db()

    film_by_id = select(models.Film).where(models.Film.id == film_id)
    result_film_by_id = database.db_session.execute(film_by_id).scalar_one()

    actors = select(models.Actor).join(models.ActorFilm, models.Actor.id == models.ActorFilm.actor_id).where(models.ActorFilm.film_id == film_id)
    result_actors = database.db_session.execute(actors).scalars()

    genres = (select(models.Genre).join(models.GenreFilm, models.Genre.genre == models.GenreFilm.genre_id).where(models.GenreFilm.film_id == film_id))
    result_genres = database.db_session.execute(genres).scalars()

    return jsonify({
        "id": result_film_by_id.id,
        "name": result_film_by_id.name,
        "poster": result_film_by_id.poster,
        "description": result_film_by_id.description,
        "rating": result_film_by_id.rating,
        "country": result_film_by_id.country,
        "added_at": result_film_by_id.added_at,
        "actors": [itm.to_dict() for itm in result_actors],
        "genres": [itm.to_dict() for itm in result_genres]
    })

@app.route('/films/<film_id>', methods=['PUT'])
def film_update(film_id):
    data = request.get_json() or {}
    database.init_db()

    new_film_query = select(models.Film).where(models.Film.id == film_id)
    new_film = database.db_session.execute(new_film_query).scalar_one()

    new_film.name = data.get("name")
    new_film.poster = data.get("poster")
    new_film.description = data.get("description")
    new_film.rating = data.get("rating")
    new_film.country = data.get("country")
    database.db_session.add(new_film)
    database.db_session.commit()

    return jsonify({"film_id": film_id})


@app.route('/films/<int:film_id>/delete', methods=['GET'])
@decorator_check_login
def film_delete(film_id):
    database.init_db()

    stmt = delete(models.Film).where(models.Film.id == film_id)
    result = database.db_session.execute(stmt)
    database.db_session.commit()

    if result.rowcount == 0:
        return jsonify({"error": "Film not found"}), 404

    return jsonify({"film_id": film_id})



@app.route('/films/<film_id>/rating', methods=['POST'])
def film_rating(film_id):
    return f"Film {film_id} rated"

@app.route('/films/<int:film_id>/rating', methods=['GET'])
def film_rating_info(film_id):
    database.init_db()


    ratings_query = select(models.Feedback).where(models.Feedback.film == film_id)
    ratings = database.db_session.execute(ratings_query).scalars()

    grades_query = select(func.avg(models.Feedback.grade).label('average'), func.count(models.Feedback.id).label('ratings_count')).where(models.Feedback.film == film_id)
    grade = database.db_session.execute(grades_query).fetchone()

    return jsonify({
        "film_id": film_id,
        "average_rating": grade[0],
        "ratings_count": grade[1],
        "ratings": [r.to_dict() for r in ratings]
    })


@app.route('/films/<int:film_id>/rating/<feedback_id>/delete', methods=['GET'])
def film_rating_delete(film_id, feedback_id):
    database.init_db()

    stmt = delete(models.Feedback).where(
        models.Feedback.id == feedback_id,
        models.Feedback.film == film_id
    )

    res = database.db_session.execute(stmt)
    database.db_session.commit()

    if res.rowcount == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})


@app.route('/films/<film_id>/rating/<feedback_id>', methods=['POST'])
def film_rating_update(film_id, feedback_id):
    database.init_db()
    data = request.get_json() or {}

    stmt = (
        update(models.Feedback)
        .where(models.Feedback.id == feedback_id, models.Feedback.film == film_id)
        .values(
            grade=data.get("grade"),
            description=data.get("description")
        )
    )
    res = database.db_session.execute(stmt)
    database.db_session.commit()

    if res.rowcount == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})

@app.route('/films/<film_id>/rating/<feedback_id>/feedback', methods=['GET'])
def film_rating_feedback(film_id, feedback_id):
    database.init_db()

    stmt = (select(models.Feedback.description, models.Feedback.grade).where(models.Feedback.film == film_id, models.Feedback.id == feedback_id))
    row = database.db_session.execute(stmt).fetchone()

    if row is None:
        return jsonify({"error": "Feedback not found"}), 404

    return jsonify({
        "film_id": film_id,
        "feedback_id": feedback_id,
        "description": row[0],
        "grade": row[1]
    })

@app.route('/users/<user_id>/list', methods=['GET'])
def user_list(user_id):# get all user lists
    database.init_db()
    lists_query = select(models.FilmList).filter_by(user_id=user_id)
    lists = database.db_session.execute(lists_query).scalars().all()
    return f"All user lists: {lists}"

@app.route('/users/<user_id>/list', methods=['POST'])
def create_user_list(user_id): # create new list
    database.init_db()
    pass

@app.route('/users/<user_id>/list/<list_id>', methods=['GET', 'POST'])
@decorator_check_login
def user_list_item(user_id, list_id):
    database.init_db()
    if request.method == "POST": #add film to list
        if user_id != session.get('user_id'):
            return "You can edit only your prifile"

        film_id = request.form["film_id"]
        list = models.FilmList(film_id=film_id, list_id=list_id)

        database.db_session.add(list)
        database.db_session.commit()
        return f'User {user_id} list item {list_id}'
    else:
        list_query = select(models.FilmList).join(models.Film, models.FilmList.film_id == models.Film.id).filter_by(list_id=list_id)
        get_list = database.db_session.execute(list_query).scalars().all()
        return f"List {list_id}: {get_list}"


@app.route('/users/<user_id>/list/<list_id>/<film_id>/delete', methods=['GET'])
@decorator_check_login
@check_user_allowance
def user_list_item_delete(user_id, list_id, film_id):
        database.init_db()
        deleted_film = delete(models.FilmList).where(models.FilmList.film_id == film_id, models.FilmList.list_id == list_id)
        database.db_session.execute(deleted_film)
        database.db_session.commit()
        return f'User {user_id} list item {film_id} from list {list_id} deleted'


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)