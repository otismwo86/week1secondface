from fastapi import *
from fastapi.responses import FileResponse, JSONResponse,HTMLResponse,RedirectResponse
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
import uvicorn
import mysql.connector 
from mysql.connector import errors
from datetime import date, datetime, timedelta,timezone
import decimal
from typing import Optional
import json
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import jwt
import datetime as dt
import httpx


app=FastAPI()



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "yeahyeah" 
app.mount("/week1secondface", StaticFiles(directory="html"), name="static")
templates = Jinja2Templates(directory="html")


def create_jwt_token(user_id: int, name: str, email: str):
    to_encode = {"sub": user_id, "name": name, "email": email}
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def decode_jwt_token(token:str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
def connect_to_db():
    return mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345678",
    database="attractions"
)
def validate_user(email,password):
     db_connection = connect_to_db()
     cursor = db_connection.cursor()
     query = "select id,name,email from member where email = %s and password = %s"
     cursor.execute(query,(email,password))
     result = cursor.fetchone()
     cursor.close()
     db_connection.close()
     if result:
          return {"id": result[0], "name": result[1], "email": result[2]}
     return None
def serialize_data(data):
    for key, value in data.items():
        if isinstance(value, decimal.Decimal):
            data[key] = float(value)
        elif isinstance(value, (dt.date, dt.datetime)):
            data[key] = value.isoformat()
    return data

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/attraction/{attractionId}", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("attractionpage.html", {"request": request})
@app.get("/api/user/auth")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_jwt_token(token)
    return {"user_id": payload["sub"], "name": payload["name"], "email": payload["email"]}
      

@app.put("/api/user/auth")
async def sign_in(request: Request):
     data = await request.json()
     email = data.get("email")
     password = data.get("password")
     user = validate_user(email,password)
     if user:
        token = create_jwt_token(user["id"],user["name"],user["email"])
        return JSONResponse(content={"token":token}, status_code = 200)
     else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="帳號或密碼錯誤或其他原因"
        )


@app.post("/api/user")
async def register(request: Request):
    data = await request.json()
    name = data.get("registername")
    email = data.get("registeremail")
    password = data.get("registerpassword")

    try:
        db_connection = connect_to_db()
        cursor = db_connection.cursor()
        query = "SELECT * FROM member WHERE email = %s"
        cursor.execute(query, (email,))
        if cursor.fetchone():
            return JSONResponse(content={"message": "電子信箱已被註冊"}, status_code=400)
        insert_query = "INSERT INTO member (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (name, email, password))
        db_connection.commit()
        cursor.close()
        return JSONResponse(content={"message": "註冊成功"}, status_code=201)
    finally:
        db_connection.close()


@app.get("/booking", response_class=HTMLResponse)
async def home(request: Request):  
    return templates.TemplateResponse("checkbooking.html", {"request": request}) 

@app.get("/thankyou", response_class=HTMLResponse)
async def thankyou(request: Request,number : int = Query(default=1)):
    return templates.TemplateResponse("thankyou.html",{"request": request,"number": number})

#booking api
#fetch行程
@app.get("/api/booking")
async def home(token: str = Depends(oauth2_scheme)):  
    payload = decode_jwt_token(token)
    user_id = payload["sub"]
    try:
        db_connection = connect_to_db()
        cursor = db_connection.cursor(dictionary=True)
        query="""select Bookings.id, attractions.name, Bookings.date, Bookings.time, Bookings.price, attractions.address, attractions.id as attrid, attractions.file
                from Bookings Join attractions on Bookings.attraction_id = attractions.id where Bookings.user_id = %s"""
        cursor.execute(query, (user_id,))
        bookings = cursor.fetchone()
        serialized_bookings = serialize_data(bookings)

        image_urls = json.loads(serialized_bookings["file"])
        first_image_url = image_urls[0]
        response_data = {
                "data": {
                    "attraction": {
                        "id": serialized_bookings["attrid"],
                        "name": serialized_bookings["name"],
                        "address": serialized_bookings["address"],
                        "image": first_image_url
                    },
                    "date": serialized_bookings["date"],
                    "time": serialized_bookings["time"],
                    "price": serialized_bookings["price"]
                }
            }
        cursor.close()
        return JSONResponse(content=response_data, status_code=200)
    finally:
        db_connection.close()

#建立行程
@app.post("/api/booking")
async def create_booking(request: Request, token: str = Depends(oauth2_scheme)):
    data = await request.json()
    payload = decode_jwt_token(token)
    user_id = payload["sub"]
    attraction_id = data.get("attraction_id")
    date = data.get("date")
    time = data.get("time")
    price = data.get("price")

    try:
        db_connection = connect_to_db()
        cursor = db_connection.cursor()

        delete_query = "DELETE FROM Bookings WHERE user_id = %s"
        cursor.execute(delete_query, (user_id,))
        
        insert_query = """
            INSERT INTO Bookings (user_id, attraction_id, date, time, price)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (user_id, attraction_id, date, time, price))
        db_connection.commit()
        cursor.close()
        return JSONResponse(content={"ok": True}, status_code=200)
    except ValueError:
        return JSONResponse(content={"error": True, "message": "輸入不正確或其他原因"}, status_code=400)
    except KeyError:
        return JSONResponse(content={"error": True, "message": "請求數據格式錯誤"}, status_code=400)
    except Exception:
        return JSONResponse(content={"error": True, "message": "伺服器內部錯誤"}, status_code=500)
    finally:
        db_connection.close()

#刪除行程
@app.delete("/api/booking")
async def home(request: Request,token: str = Depends(oauth2_scheme)):  
    payload = decode_jwt_token(token)
    user_id = payload["sub"]
    try:
         db_connection = connect_to_db()
         cursor = db_connection.cursor()
         query = "DELETE FROM Bookings WHERE user_id = %s"
         cursor.execute(query,(user_id,))
         db_connection.commit()
         cursor.close()
         return JSONResponse(content={"ok": True}, status_code=200)
    except Exception:
        raise HTTPException(status_code=500, detail={"error": True, "message": "伺服器錯誤"})
    finally:
        db_connection.close()
        
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = validate_user(form_data.username, form_data.password)
    token = create_jwt_token(user["id"], user["name"], user["email"])
    return {"access_token": token, "token_type": "bearer"}  
# Static Pages (Never Modify Code in this Block)
@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")
@app.get("/attraction/{id}", include_in_schema=False)
async def attraction(request: Request, id: int):
	return FileResponse("./static/attraction.html", media_type="text/html")
@app.get("/booking", include_in_schema=False)
async def booking(request: Request):
	return FileResponse("./static/booking.html", media_type="text/html")
@app.get("/thankyou", include_in_schema=False)
async def thankyou(request: Request):
	return FileResponse("./static/thankyou.html", media_type="text/html")


@app.get("/api/attractions")
async def getattractions(request: Request, page: int = Query(..., ge=0), keyword: str = Query(None)):
    try:
        db_connection = connect_to_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")
    
    try:
        cursor = db_connection.cursor(dictionary=True)
        item_per_page = 12
        offset = page * item_per_page
        like_keyword = f"%{keyword}%" if keyword else None
        #抓出總共有多少向，用在後面的exception
        count_query = "SELECT COUNT(*) as total FROM attractions"
        cursor.execute(count_query)
        total_items = cursor.fetchone()["total"]
        count_query_keyword = """
            SELECT COUNT(*) as total
            FROM attractions a 
            JOIN categories c ON a.category_id = c.id 
            JOIN mrt_stations m ON a.mrt_id = m.id 
            WHERE a.name LIKE %s OR m.name LIKE %s"""
        cursor.execute(count_query_keyword, (like_keyword,like_keyword))
        total_items_keyword = cursor.fetchone()["total"]
        if keyword:
            query = """
            SELECT 
                a.id,
                a.name,
                c.name AS category,
                a.description,
                a.address,
                a.direction AS transport,
                m.name AS mrt,
                a.latitude AS lat,
                a.longitude AS lng,
                a.file AS images
            FROM 
                attractions a
            JOIN 
                categories c ON a.category_id = c.id
            JOIN 
                mrt_stations m ON a.mrt_id = m.id
            WHERE a.name LIKE %s OR m.name LIKE %s
            ORDER BY
                a.id
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (like_keyword, like_keyword, item_per_page, offset))
        else:
            query = """
            SELECT 
                a.id,
                a.name,
                c.name AS category,
                a.description,
                a.address,
                a.direction AS transport,
                m.name AS mrt,
                a.latitude AS lat,
                a.longitude AS lng,
                a.file AS images
            FROM 
                attractions a
            JOIN 
                categories c ON a.category_id = c.id
            JOIN 
                mrt_stations m ON a.mrt_id = m.id
            ORDER BY
                a.id
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (item_per_page, offset))
        
        data = cursor.fetchall()
        if not keyword:
            nextPage = page + 1 if total_items > offset + item_per_page else None
        else:
            nextPage = page +1 if total_items_keyword > offset + item_per_page else None
        if not data:
            raise HTTPException(status_code=400, detail="Wrong page number")
        
        # 確保 images 欄位是 JSON 格式
        for item in data:
            if item.get('images'):
                    item['images'] = json.loads(item['images'])
                
        
        return {'nextPage': nextPage, 'data': data}
    except errors.Error as e:
        raise HTTPException(status_code=500, detail="An error occurred while executing the query.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        cursor.close()
        db_connection.close()
@app.get("/api/attractions/{attractionId}")
async def attractionIdsearch(request: Request, attractionId: int):
    try:
        db_connection = connect_to_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")
    
    try:
        cursor = db_connection.cursor(dictionary=True)#這樣返回的結果會是一個字典，方便轉換為 JSON。
        cursor.execute( """
		SELECT 
			a.id,
			a.name,
            c.name AS category,
			a.description,
			a.address,
			a.direction As transport,
            m.name AS mrt,
            a.latitude As lat,
			a.longitude As lng,
			a.file As images
			
			
		FROM 
			attractions a
		JOIN 
			categories c ON a.category_id = c.id
		JOIN 
			mrt_stations m ON a.mrt_id = m.id
		WHERE 
			a.id = %s;
		""", (attractionId,))
        result = cursor.fetchone()
        cursor.close()
        db_connection.close()

        if result is None:
            raise HTTPException(status_code=400, detail="Wrong attraction ID")
        if result.get('images'):       
            result['images'] = json.loads(result['images'])

        result = serialize_data(result)  # 序列化日期和小數類型

        return JSONResponse(content={"data": result})
    except errors.Error as e:
        
        raise HTTPException(status_code=500, detail="An error occurred while executing the query.")
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    

@app.get("/api/mrts")
async def SearchAllmrt(request: Request):
	try:
		db_connection = connect_to_db()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")
		
	
	try:
		cursor = db_connection.cursor()
		cursor.execute("Select name from(Select mrt_stations.name, Count(attractions.mrt_id) as count from mrt_stations join attractions on mrt_stations.id = attractions.mrt_id group by mrt_stations.name order by count desc) as subquery")
		result = cursor.fetchall()
		cursor.close()
		db_connection.close()

		mrt_names = [row[0] for row in result]

		return JSONResponse(content={"data": mrt_names})
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"An error occurred while executing the query.: {e}")


def generate_order_number(cursor):
    today = dt.date.today().strftime('%Y%m%d')
    query = "SELECT COUNT(*) FROM orders WHERE order_date = %s"
    cursor.execute(query, (today,))
    result = cursor.fetchone()
    count = result[0] if result else 0
    order_number = f"{today}{count + 1:03d}"
    return order_number
    


TAPPAY_API_URL = "https://sandbox.tappaysdk.com/tpc/payment/pay-by-prime"

@app.get("/api/orders/{ordernumber}")
async def check_order(request: Request,ordernumber: int):
    db_connection = connect_to_db()
    cursor = db_connection.cursor(dictionary=True)
    try:
        query = """
        select * from orders where order_number = %s
        """
        cursor.execute(query,(ordernumber,))  
        result = cursor.fetchone()
        if result is not None:
            result = serialize_data(result)
            response_data = {
                "number": result["order_number"],
                "price": result["price"],
                "trip": {
                    "attraction": {
                        "id": result["attraction_id"],
                        "name": result["attraction_name"],
                        "address": result["attraction_address"],
                        "image": result["attraction_image"]
                    },
                    "date": result["trip_date"],
                    "time": result["trip_time"]
                },
                "contact": {
                    "name": result["contact_name"],
                    "email": result["contact_email"],
                    "phone": result["contact_phone"]
                },
                "status": result["status"]
            }
            return JSONResponse(content={"data": response_data})
        return JSONResponse(content={"data": result})
    finally:
        cursor.close()
        db_connection.close()

@app.post("/api/orders")
async def create_order(request: Request):
    request_data = await request.json()
    prime = request_data.get("prime")
    order_data = request_data.get("order")

    if not prime or not order_data:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    db_connection = connect_to_db()
    cursor = db_connection.cursor()
    try:
        # 生成訂單編號
        order_number = generate_order_number(cursor)
        print(order_number)

        # 插入新訂單
        insert_order_query = """
        INSERT INTO orders (order_number, order_date, price, status, attraction_id, attraction_name, attraction_address, attraction_image, trip_date, trip_time, contact_name, contact_email, contact_phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_order_query, (
            order_number, dt.date.today(), order_data["price"], "UNPAID",
            order_data["trip"]["attraction"]["id"], order_data["trip"]["attraction"]["name"],
            order_data["trip"]["attraction"]["address"], order_data["trip"]["attraction"]["image"],
            order_data["trip"]["date"], order_data["trip"]["time"],
            order_data["contact"]["name"], order_data["contact"]["email"], order_data["contact"]["phone"]
        ))
        db_connection.commit()

        # 構建 TapPay API 請求體
        payload = {
            "prime": prime,
            "partner_key": "partner_AsK4q9j742wScTKYrnaIjS0VuX5xKa5506PsWL9jty3wUBubPQjUgf8g",
            "merchant_id": "otismo86_CTBC",
            "amount": order_data["price"],
            "currency": "TWD",
            "order_number": order_number,
            "details": "Taipei Day Trip Payment",
            "cardholder": {
                "phone_number": order_data["contact"]["phone"],
                "name": order_data["contact"]["name"],
                "email": order_data["contact"]["email"],
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": "partner_AsK4q9j742wScTKYrnaIjS0VuX5xKa5506PsWL9jty3wUBubPQjUgf8g"
        }

        # 發送請求至 TapPay API
        async with httpx.AsyncClient() as client:
            response = await client.post(TAPPAY_API_URL, headers=headers, json=payload)
            payment_result = response.json()

            if payment_result['status'] == 0:
                # 付款成功，更新訂單狀態為 PAID
                update_order_query = "UPDATE orders SET status = 'PAID' WHERE order_number = %s"
                cursor.execute(update_order_query, (order_number,))
                db_connection.commit()
                return {"order_number": order_number, "status": "PAID"}
            else:
                return {"order_number": order_number, "status": "UNPAID", "message": payment_result['msg']}


    finally:
        cursor.close()
        db_connection.close()
