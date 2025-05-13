import flask_login
import os
import data
from flask import Flask, render_template, request
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.utils import redirect
from data import db_session, Category, Product, CartsProduct, Cart
from data.users import User
from forms import RegisterForm, LoginForm, ProfileForm, ProductForm, PaymentForm

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
db_session.global_init("db/database.db")
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/static/img'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = "shop"
login_manager = LoginManager()
login_manager.init_app(app)

summa = 0


@app.route('/')
def base():
    db_sess = db_session.create_session()
    res = db_sess.query(Category.Name).all()
    categories = [category[0] for category in res]
    return render_template('main.html', title='Главная страница', categories=categories)


@app.route('/<site>', methods=['GET', 'POST'])
def register(site):
    name = str(request.url).split('/')[-1]
    db_sess = db_session.create_session()
    if request.method == 'POST': # 108-119
        if flask_login.current_user.is_anonymous: #неск. фото
            return redirect('/registration')
        elif not flask_login.current_user.is_anonymous:
            user = db_sess.query(User).filter(User.id == flask_login.current_user.id).first()
            data.add_to_cart(user, int(request.form['add']))
    id = db_sess.query(Category.Id).filter(Category.Name == name).first()[0]
    products = db_sess.query(Product.Name, Product.Price, Product.ImageId, Product.Id,
                             Product.Count).filter(
        Product.Category == int(id)).all()
    return render_template('category.html', title=f'{str(site).capitalize()}', products=products,
                           cat=f'{str(site).capitalize()}')


@app.route('/<site>/<int:prod>', methods=['GET', 'POST'])
def prod(site, prod):
    db_sess = db_session.create_session()
    id = int(str(request.url).split('/')[-1])
    if request.form.get("add"):
        if flask_login.current_user.is_anonymous:
            return redirect('/registration')
        elif not flask_login.current_user.is_anonymous:
            user = db_sess.query(User).filter(User.id == flask_login.current_user.id).first()
            data.add_to_cart(user, id)
    if request.form.get("delete"):
        product = db_sess.query(Product).filter(Product.Id == id).first()
        img = db_sess.query(Product.ImageId).filter(Product.Id == id).first()
        try:
            os.remove(f'./static/img/{img[0]}.jpg')
        except Exception:
            pass
        db_sess.delete(product)
        db_sess.commit()
        return redirect(f'/{site}')
    res = db_sess.query(Product.Name, Product.Price, Product.Description, Product.ImageId,
                        Product.Count).filter(
        Product.Id == id).all()[0]
    return render_template('product.html', title=res[0], product=res, Cate=site)


@app.route('/cart')
def cart():
    global summa
    summa = 0
    db_sess = db_session.create_session()
    res = db_sess.query(Cart.Id).filter(Cart.Owner == flask_login.current_user.id).first()
    prodct = db_sess.query(CartsProduct.ProductId, CartsProduct.Id).filter(
        CartsProduct.OwnerCart == res[0]).all()
    products = []
    for i in prodct:
        product = db_sess.query(Product).filter(Product.Id == i[0]).first()
        price = db_sess.query(Product.Price).filter(Product.Id == i[0]).first()
        summa += price[0]
        id = i[1]
        products.append([product, id])
    return render_template('cart.html', title='Коризна', products=products, summ=summa)


@app.route('/payment', methods=['GET', 'POST'])
def payment():
    global summa
    form = PaymentForm()
    if request.method == 'POST':
        db_sess = db_session.create_session()
        owner = db_sess.query(Cart.Id).filter(Cart.Owner == flask_login.current_user.id).first()
        res = db_sess.query(CartsProduct).filter(CartsProduct.OwnerCart == owner[0]).all()
        for product in res:
            db_sess.delete(product)
            db_sess.commit()
        summa = 0
        return redirect('/u')
    return render_template('payment.html', title='Оплата', form=form, summ=summa)


@app.route('/success')
def success():
    return render_template('success.html', title='Успешная оплата')


@app.route('/delete/<product>')
def cart_del(product):
    global summa
    db_sess = db_session.create_session()
    res = db_sess.query(CartsProduct).filter(CartsProduct.Id == product).first()
    db_sess.delete(res)
    db_sess.commit()
    summa = 0
    return redirect('/cart')


@app.route('/delete_product')
def prod_del():
    db_sess = db_session.create_session()
    product = db_sess.query(Product).filter().first()
    db_sess.delete(product)
    db_sess.commit()
    return redirect('/')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('registration.html', title='Регистрация',
                                   form=form,
                                   message="Введенные пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.id == form.email.data).first():
            return render_template('registration.html', title='Регистрация',
                                   form=form,
                                   message="Данный пользователь уже зарегистрирован")
        data.user_create(id=form.email.data,
                         name=form.name.data,
                         status=0,
                         password=form.password.data)
        return redirect('/login')
    return render_template('registration.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Профиль')


@login_required
@app.route('/delete_profile', methods=['GET', 'POST'])
def delete_profile():
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == flask_login.current_user.id).first()
    i_d = db_sess.query(Cart.Id).filter(Cart.Owner == flask_login.current_user.id).first()
    car_t = db_sess.query(Cart).filter(Cart.Owner == flask_login.current_user.id).first()
    prd = db_sess.query(CartsProduct).filter(CartsProduct.OwnerCart == i_d[0]).all()
    for i in prd:
        db_sess.delete(i)
    db_sess.delete(car_t)
    db_sess.delete(user)
    db_sess.commit()
    return redirect('/')


@app.route('/change_profile', methods=['GET', 'POST'])
@login_required
def change_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('change_profile.html', title='Изменение профиля',
                                   form=form,
                                   message="Введенные пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.id == form.email.data).first():
            if form.email.data == flask_login.current_user.id:
                pass
            else:
                return render_template('change_profile.html', title='Изменение профиля',
                                       form=form,
                                       message="Данный пользователь уже зарегистрирован")
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == flask_login.current_user.id).first()
        user.id = form.email.data
        user.set_password(form.password.data)
        user.Name = form.name.data
        db_sess.commit()
        login_user(user, remember=False)
        return redirect('/profile')
    return render_template('change_profile.html', title='Изменение профиля', form=form)


@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    db_sess = db_session.create_session()
    res = db_sess.query(Category.Id, Category.Name).all()
    form.category.choices = [category[1] for category in res]
    if form.validate_on_submit():
        data.add_product(form.name.data,
                         form.description.data,
                         form.price.data,
                         form.count.data,
                         form.image,
                         form, res)
        return redirect("/add_product")
    return render_template('add_product.html', title='Добавление товара', form=form)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/about')
def about():
    return render_template('about.html', title='О Vladimir Kobzev')


@app.route('/developers')
def developers():
    return render_template('developers.html', title='Создатель')


if __name__ == '__main__':
    app.run()