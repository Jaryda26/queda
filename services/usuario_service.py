import bcrypt
from db import ejecutar_query,obtener_dataframe

def registrar_usuario(n,e,p):
 h=bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()
 ejecutar_query("insert into gastos.usuarios(nombre,email,password_hash) values(:n,:e,:h)",{'n':n,'e':e,'h':h})

def validar_usuario(e,p):
 df=obtener_dataframe(f"select * from gastos.usuarios where email='{e}'")
 if df.empty:return None
 u=df.iloc[0]
 try:
  return u if bcrypt.checkpw(p.encode(),str(u['password_hash']).encode()) else None
 except: return None
