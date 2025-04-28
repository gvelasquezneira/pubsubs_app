import os
from sqlalchemy import Column, String, Float, text, bindparam
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, make_response, request
import csv
from io import StringIO

app = Flask(__name__)
db = SQLAlchemy()

db_path = os.path.abspath('publix.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db.init_app(app)

class Product(db.Model):
    __tablename__ = 'products'
    
    ID = Column(String, primary_key=True)
    Store_ID = Column("Store ID", String)
    Location = Column(String)
    Category = Column(String)
    Product_Name = Column("Product Name", String)
    Price = Column(Float)
    Size = Column(String)
    Date = Column(String)
    City = Column(String)

@app.route('/')
def index():
    try:
        result = db.session.execute(text("SELECT DISTINCT City FROM products WHERE City IS NOT NULL AND City != '' ORDER BY City"))
        cities = [row[0] for row in result]
        return render_template('index.html', cities=cities)
    except Exception as e:
        return render_template('error.html', 
                              heading='Database Connection Failed',
                              error_message=str(e))
    
@app.route('/categories')
def list_categories():
    try:
        result = db.session.execute(text("SELECT DISTINCT Category FROM products WHERE Category IS NOT NULL AND Category != '' ORDER BY Category"))
        categories = [row[0] for row in result]
        return render_template('categories.html', categories=categories)
    except Exception as e:
        return render_template('error.html', 
                              heading='Error loading categories',
                              error_message=str(e))

@app.route('/city/<city_name>')
def view_city(city_name):
    try:
        query = text("""
            SELECT DISTINCT "Store ID" as store_id, Location 
            FROM products 
            WHERE City = :city_name
            ORDER BY Location
        """)
        result = db.session.execute(query, {"city_name": city_name})
        location_list = []
        for row in result:
            store_id = row[0]
            location = row[1]
            if store_id and location:
                location_list.append({
                    'Store_ID': store_id,
                    'Location': location
                })
        return render_template('city.html', 
                             city=city_name,
                             locations=location_list)
    except Exception as e:
        return render_template('error.html', 
                              heading=f'Error viewing locations in {city_name}',
                              error_message=str(e))

@app.route('/location/<store_id>')
def view_location(store_id):
    try:
        query = text("""
            SELECT DISTINCT "Store ID" as store_id, Location, City
            FROM products 
            WHERE "Store ID" = :store_id
            LIMIT 1
        """)
        store_info = db.session.execute(query, {"store_id": store_id}).first()
        if not store_info:
            return render_template('error.html',
                                 heading='Store Not Found',
                                 error_message=f'No store found with ID: {store_id}')
        location_info = {
            'Store_ID': store_info[0],
            'Location': store_info[1],
            'City': store_info[2]
        }
        count_query = text("""
            SELECT COUNT(*) 
            FROM products 
            WHERE "Store ID" = :store_id
        """)
        product_count = db.session.execute(count_query, {"store_id": store_id}).scalar()
        products_query = text("""
            SELECT ID, "Store ID" as store_id, Location, Category, "Product Name" as product_name, 
                   Price, Size, Date, City
            FROM products 
            WHERE "Store ID" = :store_id
            ORDER BY Category, "Product Name"
            LIMIT 5000
        """)
        product_rows = db.session.execute(products_query, {"store_id": store_id}).all()
        products = []
        for row in product_rows:
            product = {
                'ID': row[0],
                'Store_ID': row[1],
                'Location': row[2],
                'Category': row[3],
                'Product_Name': row[4],
                'Price': row[5],
                'Size': row[6],
                'Date': row[7],
                'City': row[8]
            }
            products.append(product)
        categories_query = text("""
            SELECT DISTINCT Category
            FROM products 
            WHERE "Store ID" = :store_id
            ORDER BY Category
        """)
        categories = [row[0] for row in db.session.execute(categories_query, {"store_id": store_id}).all()]
        return render_template('location.html',
                             location=location_info,
                             products=products,
                             product_count=product_count,
                             categories=categories)
    except Exception as e:
        return render_template('error.html', 
                              heading=f'Error viewing store {store_id}',
                              error_message=str(e))

@app.route('/location/<store_id>/category/<category_name>')
def view_location_by_category(store_id, category_name):
    try:
        query = text("""
            SELECT DISTINCT "Store ID" as store_id, Location, City
            FROM products 
            WHERE "Store ID" = :store_id
            LIMIT 1
        """)
        store_info = db.session.execute(query, {"store_id": store_id}).first()
        if not store_info:
            return render_template('error.html',
                                 heading='Store Not Found',
                                 error_message=f'No store found with ID: {store_id}')
        location_info = {
            'Store_ID': store_info[0],
            'Location': store_info[1],
            'City': store_info[2]
        }
        count_query = text("""
            SELECT COUNT(*) 
            FROM products 
            WHERE Category = :category_name
        """)
        count = db.session.execute(count_query, {"category_name": category_name}).scalar()

        products_query = text("""
            SELECT ID, "Store ID" as store_id, Location, Category, "Product Name" as product_name, 
                   Price, Size, Date, City
            FROM products 
            WHERE Category = :category_name
            ORDER BY "Product Name"
            LIMIT 5000
        """)
        product_rows = db.session.execute(products_query, {"category_name": category_name}).all()
        products = []
        store_ids = set()  
        for row in product_rows:
            product = {
                'ID': row[0],
                'Store_ID': row[1],
                'Location': row[2],
                'Category': row[3],
                'Product_Name': row[4],
                'Price': row[5],
                'Size': row[6],
                'Date': row[7],
                'City': row[8]
            }
            products.append(product)
            store_ids.add(row[1])

        # Calculate avg prices
        if products:
            current_avg_price = sum(product['Price'] for product in products) / len(products)
        else:
            current_avg_price = 0

        # Calculate avg price vs other stores in same category
        if store_ids:
            other_avg_query = text("""
                SELECT AVG(Price)
                FROM products
                WHERE Category = :category_name
                AND "Store ID" NOT IN :store_ids
            """).bindparams(bindparam("store_ids", expanding=True))
            other_avg_result = db.session.execute(
                other_avg_query,
                {"category_name": category_name, "store_ids": tuple(store_ids)}
            ).scalar()
            other_avg_price = other_avg_result if other_avg_result is not None else 0
        else:
            other_avg_query = text("""
                SELECT AVG(Price)
                FROM products
                WHERE Category = :category_name
            """)
            other_avg_price = db.session.execute(
                other_avg_query,
                {"category_name": category_name}
            ).scalar() or 0

        return render_template('category.html', 
                              products=products, 
                              category_name=category_name,
                              count=count,
                              current_avg_price=current_avg_price,
                              other_avg_price=other_avg_price)
    except Exception as e:
        return render_template('error.html', 
                              heading=f'Error viewing {category_name} category',
                              error_message=str(e))

@app.route('/category/<category_name>')
def view_category(category_name):
    try:
        count_query = text("""
            SELECT COUNT(*) 
            FROM products 
            WHERE Category = :category_name
        """)
        count = db.session.execute(count_query, {"category_name": category_name}).scalar()
        products_query = text("""
            SELECT ID, "Store ID" as store_id, Location, Category, "Product Name" as product_name, 
                   Price, Size, Date, City
            FROM products 
            WHERE Category = :category_name
            ORDER BY "Product Name"
            LIMIT 5000
        """)
        product_rows = db.session.execute(products_query, {"category_name": category_name}).all()
        products = []
        for row in product_rows:
            product = {
                'ID': row[0],
                'Store_ID': row[1],
                'Location': row[2],
                'Category': row[3],
                'Product_Name': row[4],
                'Price': row[5],
                'Size': row[6],
                'Date': row[7],
                'City': row[8]
            }
            products.append(product)
        return render_template('category.html', 
                              products=products, 
                              category_name=category_name,
                              count=count)
    except Exception as e:
        return render_template('error.html', 
                              heading=f'Error viewing {category_name} category',
                              error_message=str(e))

from flask import request

@app.route('/analyze')
def analyze():
    try:
        # Get filter parameters from query string
        selected_store = request.args.get('store')
        selected_category = request.args.get('category')

        # Get all unique stores (locations) and categories for filter buttons
        stores_result = db.session.execute(text('SELECT DISTINCT "Location", "Store ID" FROM products ORDER BY "Location"'))
        stores = [{'location': row[0], 'store_id': row[1]} for row in stores_result]
        categories_result = db.session.execute(text('SELECT DISTINCT Category FROM products ORDER BY Category'))
        categories = [row[0] for row in categories_result]

        analysis = []

        # Only run analysis if both filters are selected
        if selected_store and selected_category:
            # Get all products for this store and category
            products_query = text("""
                SELECT "Product Name", AVG(Price) as avg_price
                FROM products
                WHERE "Store ID" = :store_id AND Category = :category
                GROUP BY "Product Name"
            """)
            store_products = db.session.execute(
                products_query,
                {'store_id': selected_store, 'category': selected_category}
            ).fetchall()

            for row in store_products:
                product_name = row[0]
                your_price = row[1]

                # Calculate avg price in other stores for this product and category
                other_avg_query = text("""
                    SELECT AVG(Price)
                    FROM products
                    WHERE Category = :category
                    AND "Store ID" != :store_id
                    AND "Product Name" = :product_name
                """)
                other_avg_price = db.session.execute(
                    other_avg_query,
                    {
                        'category': selected_category,
                        'store_id': selected_store,
                        'product_name': product_name
                    }
                ).scalar() or 0

                diff = your_price - other_avg_price
                analysis.append({
                    'product_name': product_name,
                    'your_price': your_price,
                    'other_avg_price': other_avg_price,
                    'diff': diff
                })

        return render_template(
            'analyze.html',
            stores=stores,
            categories=categories,
            selected_store=selected_store,
            selected_category=selected_category,
            analysis=analysis
        )
    except Exception as e:
        return render_template('error.html',
                              heading='Error analyzing prices',
                              error_message=str(e))
if __name__ == '__main__':
    app.run(debug=True)