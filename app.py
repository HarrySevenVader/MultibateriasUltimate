# BACKEND - Multibaterias.                             
# Servidor, parte donde el usuario comun no puede ver. 
# Programador: HarrySev.                               

# Librerias a utilizar:
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import check_password_hash, generate_password_hash
import smtplib
import re #Esta libreria es para validar el correo 
from email.mime.text import MIMEText
import twilio
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime, timedelta
import json
from fpdf import FPDF
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# Inicializacion de la aplicacion Flask.
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuración de la base de datos.
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'admin_multibaterias'
app.config['MYSQL_PASSWORD'] = 'multibaterias4033'
app.config['MYSQL_DB'] = 'Multibaterias'


mysql = MySQL(app)



# Ruta incial (Pagina de inicio de Multibaterias).
@app.route('/')
def home():
    return render_template('index.html')


# Rutas del sistema de inicio de sesión (Administrador y Usuarios).

# Ruta de registro de usuarios dentro del sitio web.
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        nombre_completo = request.form['nombre_completo']

        # Validar que el usuario no exista ya
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM Usuarios WHERE username = %s OR email_usuario = %s", (username, email))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('El nombre de usuario o el correo electrónico ya están en uso.', 'danger')
            cursor.close()
            return redirect(url_for('register'))  # Redirigir de vuelta al registro

        # Validar el dominio del correo
        allowed_domains = ['gmail.com', 'hotmail.cl', 'utem.cl']
        email_domain = email.split('@')[-1]  # Obtener el dominio del correo
        
        if email_domain not in allowed_domains:
            flash('El correo debe ser de uno de los siguientes dominios: gmail.com, hotmail.cl, o utem.cl', 'danger')
            cursor.close()
            return redirect(url_for('register'))  # Redirigir de vuelta al registro

        # Encriptar la contraseña
        hashed_password = generate_password_hash(password)

        try:
            cursor.execute('INSERT INTO Usuarios (username, password, email_usuario, nombre_completo_usuario) VALUES (%s, %s, %s, %s)', 
                           (username, hashed_password, email, nombre_completo))
            mysql.connection.commit()

            # Borrar mensaje aqui para la entrega final
            #flash('Registro exitoso. Puedes iniciar sesión.', 'success')
            return redirect(url_for('login_oficial'))
        except Exception as e:
            flash('Error al registrar el usuario. Por favor, inténtalo de nuevo.', 'danger')
            print(f"Error al registrar: {e}")  # Registro de errores en el servidor
            mysql.connection.rollback()  # Rollback en caso de error
        finally:
            cursor.close()

    return render_template('register.html')

# Ruta para iniciar sesión.
@app.route('/login_oficial', methods=['GET', 'POST'])
def login_oficial():
    if request.method == 'POST':
        username_or_email = request.form['username']  # Puede ser nombre de usuario o correo
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Buscar al usuario por nombre de usuario o correo electrónico
        cursor.execute("SELECT id_usuario, username, password, email_usuario, rol FROM Usuarios WHERE username = %s OR email_usuario = %s", (username_or_email, username_or_email))
        user = cursor.fetchone()

        cursor.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id_usuario']
            session['username'] = user['username']  # Guardar el nombre de usuario en la sesión

            # Redirigir según el rol del usuario
            if user['rol'] == 'admin':
                return redirect(url_for('index_admin'))  # Redirige a index_admin.html
            else:
                return redirect(url_for('index_user'))  # Redirige a la página de inicio
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')  # Mensaje de error

    return render_template('login_oficial.html')


# Ruta para solicitar recuperar contraseña dentro del sitio web.
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT username FROM Usuarios WHERE email_usuario = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Generar token para el enlace de recuperación
            s = URLSafeTimedSerializer(app.secret_key)
            token = s.dumps(email, salt='recover-key')

            # Crear el enlace de recuperación
            enlace_recuperacion = url_for('restablecer_contrasena', token=token, _external=True)

            # Mensaje de correo
            mensaje = f"""
            Hola {user['username']},

            Has solicitado recuperar tu contraseña. 
            Haz clic en el siguiente enlace para restablecerla:
            {enlace_recuperacion}

            Si no solicitaste esto, ignora este correo.

            Saludos,
            Multibaterias.
            """

            try:
                # Enviar correo
                enviar_correo(email, 'Recuperación de Contraseña', mensaje)
                # Cambiar el mensaje de éxito a uno más específico
                return redirect(url_for('confirmacion', message='recuperacion_exito'))
            except Exception as e:
                # Mostrar un mensaje de éxito incluso si falla el envío del correo
                return redirect(url_for('confirmacion', message='error_en_envio'))
        else:
            # Mostrar un mensaje de éxito indicando que no se encontró el correo
            return redirect(url_for('confirmacion', message='no_encontrado'))

    return render_template('forgot_password.html')


# Ruta para definir una nueva contraseña.
@app.route('/restablecer_contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    s = URLSafeTimedSerializer(app.secret_key)

    try:
        # Verificar el token y obtener el correo
        email = s.loads(token, salt='recover-key', max_age=3600)  # El token es válido por 1 hora
    except SignatureExpired:
        flash('El enlace de recuperación ha expirado.', 'danger')
        return redirect(url_for('forgot_password'))  # Redirigir si el enlace ha expirado
    except Exception as e:
        flash(f'Error al validar el enlace: {str(e)}', 'danger')
        return redirect(url_for('forgot_password'))  # Redirigir en caso de error

    if request.method == 'POST':
        nueva_contrasena = request.form['nueva_contrasena']
        confirmar_contrasena = request.form['confirmar_contrasena']

        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('restablecer_contrasena.html', token=token)  # Mantener en la misma página

        # Generar el hash de la nueva contraseña
        hashed_password = generate_password_hash(nueva_contrasena)

        # Actualizar la contraseña en la base de datos
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE Usuarios SET password = %s WHERE email_usuario = %s", (hashed_password, email))
        mysql.connection.commit()
        cursor.close()

        #flash('Contraseña restablecida exitosamente. Puedes iniciar sesión.', 'success')
        return redirect(url_for('login_oficial'))  # Redirigir a la página de inicio de sesión

    return render_template('restablecer_contrasena.html', token=token)  # Pasar el token en el GET


# Ruta para cerrar la sesion del usuario.
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('home'))


# Rutas del usuario.

# Ruta inicial del usuario.
@app.route('/index_user')
def index_user():
    if 'username' in session:
        username = session['username']
    else:
        username = 'Invitado'
    return render_template('index_user.html', username=username)


# Ruta para mostrar el perfil del usuario
@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver tu perfil.', 'warning')
        return redirect(url_for('login_oficial'))
    
    # Aquí puedes agregar lógica para mostrar la información del perfil del usuario
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Usuarios WHERE id_usuario = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    return render_template('perfil.html', user=user)


# Ruta para actualizar el perfil del usuario
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para actualizar tu perfil.', 'warning')
        return redirect(url_for('login_oficial'))
    
    user_id = session['user_id']
    nombre_completo = request.form['name']
    email = request.form['email']
    
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE Usuarios SET nombre_completo_usuario = %s, email_usuario = %s WHERE id_usuario = %s", 
                   (nombre_completo, email, user_id))
    mysql.connection.commit()
    cursor.close()
    
    #flash('Información actualizada correctamente.', 'success')
    return redirect(url_for('perfil'))


# Rutas para agendar citas (Usuario). 

# Ruta para agendarla.
@app.route('/pedir_hora', methods=['GET', 'POST'])
def pedir_hora():
    if request.method == 'POST':
        user_id = session.get('user_id')  # Obtén el ID del usuario de la sesión
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        
        if not user_id:
            flash('Debes iniciar sesión para agendar una cita.', 'warning')
            return redirect(url_for('login_oficial'))

        # Validar que la fecha y hora no estén vacías
        if not fecha or not hora:
            flash('La fecha y la hora son obligatorias.', 'danger')
            return redirect(url_for('pedir_hora'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Verificar si ya existe una cita para el mismo día y hora
        cursor.execute('SELECT id_usuario FROM citas WHERE fecha = %s AND hora = %s', (fecha, hora))
        cita_existente = cursor.fetchone()

        if cita_existente:
            # Si la cita ya fue agendada por el mismo usuario
            if cita_existente['id_usuario'] == user_id:
                return redirect(url_for('confirmacion', message='ya_agendada'))
            # Si la cita fue agendada por otro usuario
            else:
                return redirect(url_for('confirmacion', message='ya_agendada_por_otra_persona'))

        try:
            # Intentar insertar la nueva cita
            cursor.execute('''INSERT INTO citas (id_usuario, fecha, hora) VALUES (%s, %s, %s)''', (user_id, fecha, hora))
            mysql.connection.commit()
            # Redirige a la página de confirmación con mensaje de éxito
            return redirect(url_for('confirmacion', message='cita_exito'))
        except MySQLdb.Error as db_error:
            mysql.connection.rollback()
            print(f'Error de base de datos al agendar cita: {db_error}')
            flash('Error al agendar la cita. Por favor, intenta nuevamente.', 'danger')
            return redirect(url_for('pedir_hora'))
        except Exception as e:
            mysql.connection.rollback()
            print(f'Error inesperado al agendar la cita: {e}')
            flash('Error inesperado. Por favor, intenta nuevamente.', 'danger')
            return redirect(url_for('pedir_hora'))
        finally:
            cursor.close()

    return render_template('pedir_hora1.html')

@app.route('/mis_horas')
def mis_horas():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para ver tus citas.', 'warning')
        return redirect(url_for('login_oficial'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Consulta para obtener las citas del usuario
    cursor.execute("SELECT * FROM citas WHERE id_usuario = %s", (user_id,))
    citas = cursor.fetchall()

    cursor.close()

    return render_template('mis_horas.html', citas=citas)

@app.route('/eliminar_cita', methods=['POST'])
def eliminar_cita():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para eliminar una cita.', 'warning')
        return redirect(url_for('login_oficial'))

    cita_id = request.form.get('cita_id')

    if not cita_id:
        flash('No se ha proporcionado una cita válida.', 'danger')
        return redirect(url_for('mis_horas'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Verificar si la cita pertenece al usuario
    cursor.execute("SELECT * FROM citas WHERE id_cita = %s AND id_usuario = %s", (cita_id, session['user_id']))
    cita = cursor.fetchone()

    if cita:
        # Eliminar la cita
        cursor.execute("DELETE FROM citas WHERE id_cita = %s", (cita_id,))
        mysql.connection.commit()
        flash('La cita ha sido eliminada correctamente.', 'success')  # Descomentar para mostrar mensaje
    else:
        flash('No se encontró la cita.', 'danger')

    cursor.close()

    return redirect(url_for('mis_horas'))


# Rutas del administrador.

# Ruta inicial del administrador.
@app.route('/index_admin')
def index_admin():
    if 'user_id' not in session:
        return redirect(url_for('login_oficial'))
    return render_template('index_admin.html', username=session.get('username'))


# Ruta para acceder a las consultas del formulario
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_oficial'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Contacto WHERE archivado = FALSE')
    contactos = cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html', username=session.get('username'), contactos=contactos)


# Ruta para ver el historial de consultas del formulario
@app.route('/historial')
def historial():
    if 'user_id' not in session:
        return redirect(url_for('login_oficial'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Obtener todas las consultas (archivadas y no archivadas)
    cursor.execute('SELECT * FROM Contacto')
    contactos = cursor.fetchall()
    cursor.close()

    return render_template('historial.html', username=session.get('username'), contactos=contactos)


# Ruta para gestionar a todos los usuarios y funcionalidades dentro del sitio web.
@app.route('/ver_usuarios', methods=['GET'])
def ver_usuarios():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder a esta página.', 'warning')
        return redirect(url_for('login_oficial'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Obtener todos los usuarios
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()

    # Obtener todas las citas junto con el nombre completo del usuario
    cursor.execute("""
        SELECT citas.id_cita, citas.fecha, citas.hora, usuarios.nombre_completo_usuario 
        FROM citas
        JOIN usuarios ON citas.id_usuario = usuarios.id_usuario
    """)
    citas = cursor.fetchall()

    # Obtener todos los presupuestos junto con el nombre del usuario y el detalle
    cursor.execute("""
        SELECT presupuestos.id_presupuesto, presupuestos.costo, presupuestos.fecha, presupuestos.detalle, usuarios.nombre_completo_usuario 
        FROM presupuestos
        JOIN usuarios ON presupuestos.id_usuario = usuarios.id_usuario
    """)
    presupuestos = cursor.fetchall()

    cursor.close()

    return render_template('ver_usuarios.html', username=session.get('username'), usuarios=usuarios, citas=citas, presupuestos=presupuestos)


# Ruta para borrar a un usuario del sitio web.
@app.route('/borrar_usuario/<int:user_id>', methods=['POST'])
def borrar_usuario(user_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para borrar un usuario.', 'warning')
        return redirect(url_for('login_oficial'))
    
    # Comprobar si el usuario que se intenta borrar es el admin
    if user_id == 1:  # Suponiendo que el ID del admin es 1
        flash('No se puede borrar el usuario administrador.', 'danger')
        return redirect(url_for('ver_usuarios'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Primero, eliminar todos los presupuestos del usuario
    cursor.execute("DELETE FROM presupuestos WHERE id_usuario = %s", (user_id,))

    # Primero, eliminar todas las citas del usuario
    cursor.execute("DELETE FROM citas WHERE id_usuario = %s", (user_id,))
    
    # Ahora eliminar el usuario
    cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (user_id,))
    mysql.connection.commit()

    #Borrar aqui tambien el mensaje
    #flash('Usuario y citas eliminados correctamente.', 'success')
    cursor.close()

    return redirect(url_for('ver_usuarios'))


# Ruta para eliminar una cita (Administrador).
@app.route('/eliminar_cita_admin', methods=['POST'])
def eliminar_cita_admin():
    # Obtiene el ID de la cita desde el formulario
    cita_id = request.form.get('cita_id')
    
    # Verifica que el usuario esté autenticado
    if 'user_id' not in session:
        flash('Debes iniciar sesión para eliminar una cita.', 'warning')
        return redirect(url_for('login_oficial'))

    # Crea un cursor para interactuar con la base de datos
    cursor = mysql.connection.cursor()

    # Elimina la cita utilizando el ID proporcionado
    cursor.execute("DELETE FROM citas WHERE id_cita = %s", (cita_id,))
    mysql.connection.commit()  # Guarda los cambios


    #borrar mensaje aqui igual
    #flash('Cita eliminada correctamente.', 'success')  # Mensaje de éxito
    cursor.close()  # Cierra el cursor

    return redirect(url_for('ver_usuarios'))  # Redirige a la vista de usuarios


# Ruta para enviar correos.
def enviar_correo(destinatario, asunto, mensaje):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'multibateriasmaipuss@gmail.com'  # Cambia esto por tu correo
    smtp_password = 'lnns skdv wpip wohi'  # Cambia aquí por tu contraseña de aplicación

    msg = MIMEText(mensaje)
    msg['Subject'] = asunto
    msg['From'] = smtp_user
    msg['To'] = destinatario

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print("Correo enviado exitosamente")
    except Exception as e:
        print(f'Error al enviar el correo: {str(e)}')


# Ruta para responder al usuario desde la dashboard del administrador.
@app.route('/responder_contacto', methods=['POST'])
def responder_contacto():
    if request.method == 'POST':
        # Obtener el id_contacto del formulario
        id_contacto = request.form['id_contacto']
        correo_contacto = request.form['correo_contacto']
        respuesta = request.form['respuesta']

        # Configuración del correo
        mensaje = f"Estimado usuario,\n\nEsta es la respuesta a tu consulta:\n{respuesta}\n\nSaludos,\nEquipo Multi Baterías"
        asunto = 'Respuesta a tu consulta en Multi Baterías'

        try:
            # Enviar el correo
            enviar_correo(correo_contacto, asunto, mensaje)

            # Guardar la respuesta en la base de datos
            cursor = mysql.connection.cursor()
            cursor.execute('UPDATE Contacto SET archivado = TRUE, respuesta = %s WHERE id_contacto = %s', (respuesta, id_contacto))
            mysql.connection.commit()
            cursor.close()

            flash('Respuesta enviada y consulta archivada', 'success')
        except Exception as e:
            flash(f'Error al enviar el correo o archivar la consulta: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))
    


# Ruta de mensajes de confirmacion del sitio web
@app.route('/confirmacion')
def confirmacion():
    message = request.args.get('message', 'error_desconocido')
    redirect_url = url_for('index_user')  # URL a la que quieras redirigir después de mostrar el mensaje
    return render_template('confirmation_page.html', message=message, redirect_url=redirect_url)


# Ruta del formulario de consultas basica del sitio web.
@app.route('/formulario', methods=['POST'])
def formulario():
    if request.method == 'POST':
        try:
            nombre_contacto = request.form['nombre']
            correo_contacto = request.form['email']
            sexo = request.form['sexo']
            asunto = request.form['asunto']
        except KeyError as e:
            return render_template('confirmation_page.html', message='campos_vacios', redirect_url=url_for('home'))

        # Validar dominios permitidos
        dominios_permitidos = ['@gmail.com', '@utem.cl', '@hotmail.cl']
        if not any(correo_contacto.endswith(dominio) for dominio in dominios_permitidos):
            return render_template('confirmation_page.html', message='dominio_invalido', redirect_url=url_for('home'))

        cursor = mysql.connection.cursor()
        try:
            cursor.execute('''INSERT INTO Contacto (nombre_contacto, correo_contacto, sexo, asunto) 
                              VALUES (%s, %s, %s, %s)''', (nombre_contacto, correo_contacto, sexo, asunto))
            mysql.connection.commit()

            # Verificar si el usuario está conectado antes de redirigir
            if 'username' in session:  # Si el usuario está conectado
                redirect_url = url_for('index_user')
            else:  # Si el usuario no está conectado
                redirect_url = url_for('home')

            # Muestra la página de confirmación y luego redirige
            return render_template('confirmation_page.html', message='exito', redirect_url=redirect_url)
        except MySQLdb.IntegrityError as e:
            if "1062" in str(e):
                # El correo ya está registrado, redirigir a home
                return render_template('confirmation_page.html', message='correo_repetido', redirect_url=url_for('home'))
            else:
                return render_template('confirmation_page.html', message='error_db', redirect_url=url_for('home'))
        finally:
            cursor.close()


# Proximas funciones 
@app.route('/pedir_presupuesto', methods=['GET'])
def pedir_presupuesto():
    return render_template('pedir_presupuesto.html')

@app.route('/guardar_presupuesto', methods=['POST'])
def guardar_presupuesto():
    if request.method == 'POST':
        # Captura de datos
        servicio = request.form.get('servicio')
        tipo_vehiculo = request.form.get('tipo_vehiculo')
        marca_producto = request.form.get('marca_producto')
        tipo_servicio = request.form.get('tipo_servicio')  # Nuevo campo capturado
        costo_mano_obra = request.form.get('costo_mano_obra')
        costo_producto = request.form.get('costo_producto')
        costo_total = request.form.get('costo_total')
        descripcion_adicional = request.form.get('descripcion_adicional')
        id_usuario = session['user_id']

        # Generar un código único para el presupuesto
        codigo_presupuesto = f"{id_usuario}_{int(datetime.now().timestamp())}"

        # Crear un detalle que refleje la información capturada
        detalle = (f"Servicio: {servicio}, Tipo de Vehículo: {tipo_vehiculo}, Marca: {marca_producto}, "
                   f"Tipo de Servicio: {tipo_servicio}, Costo Mano de Obra: {costo_mano_obra}, "
                   f"Costo Producto: {costo_producto}, Descripción Adicional: {descripcion_adicional}")

        cursor = mysql.connection.cursor()
        try:
            # Insertar en la base de datos
            cursor.execute('INSERT INTO Presupuestos (id_usuario, codigo_presupuesto, detalle, costo) VALUES (%s, %s, %s, %s)', 
                           (id_usuario, codigo_presupuesto, detalle, costo_total))
            mysql.connection.commit()
            flash('Presupuesto guardado exitosamente.', 'success')

        except Exception as e:
            mysql.connection.rollback()
            flash('Error al guardar el presupuesto: ' + str(e), 'error')
        finally:
            cursor.close()

        # Redirigir a la página de usuario
        return redirect(url_for('index_user'))

@app.route('/mis_presupuestos', methods=['GET'])
def mis_presupuestos():
    # Obtener presupuestos de la base de datos
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Presupuestos WHERE id_usuario = %s ORDER BY fecha DESC', (session['user_id'],))
    presupuestos = cursor.fetchall()
    cursor.close()

    # Debugging: imprimir los presupuestos obtenidos
    print(presupuestos)  # Verifica si se están obteniendo correctamente los presupuestos

    return render_template('mis_presupuestos.html', presupuestos=presupuestos)


@app.route('/eliminar_presupuesto/<int:id_presupuesto>', methods=['GET'])
def eliminar_presupuesto(id_presupuesto):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute('DELETE FROM Presupuestos WHERE id_presupuesto = %s', (id_presupuesto,))
        mysql.connection.commit()
        flash('Presupuesto eliminado exitosamente!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar el presupuesto: {e}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('mis_presupuestos'))

@app.route('/descargar_pdf/<int:id_presupuesto>')
def descargar_pdf(id_presupuesto):
    # Obtener el presupuesto por ID
    presupuesto = obtener_presupuesto_por_id(id_presupuesto)

    if presupuesto:
        # Crear un archivo PDF en memoria
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Estilos personalizados
        styles = getSampleStyleSheet()
        style_normal = styles['Normal']
        style_normal.fontName = 'Helvetica'
        style_normal.fontSize = 12
        style_normal.alignment = TA_JUSTIFY

        style_title = styles['Title']
        style_title.fontName = 'Helvetica-Bold'
        style_title.fontSize = 16
        style_title.alignment = TA_CENTER

        # Agregar el encabezado del presupuesto
        elements.append(Paragraph("Presupuesto Multi Baterías", style_title))
        elements.append(Spacer(1, 0.25 * inch))  # Espaciado

        # Insertar el logo de la empresa
        logo_path = os.path.join(app.static_folder, "images", "perfil", "Perfil.png")  # Cambiado a 'Perfil.png'
        
        try:
            logo = Image(logo_path, 2 * inch, 2 * inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 0.25 * inch))  # Espaciado debajo del logo
        except OSError as e:
            return f"Error al abrir la imagen: {e}", 500  # Manejo de error si la imagen no se puede abrir


         # Agregar un espacio adicional de 3 líneas
        elements.append(Spacer(1, 6 * 0.1 * inch))  # Espaciado adicional (3 líneas)

        # Información del presupuesto
        elements.append(Paragraph(f"Código de Presupuesto: {presupuesto['codigo_presupuesto']}", style_normal))
        elements.append(Spacer(1, 0.2 * inch))  # Espacio entre el código y el nombre

        # Aquí usas el nombre del usuario obtenido de la consulta
        nombre_usuario = presupuesto['nombre_completo_usuario']
        elements.append(Paragraph(f"Nombre: {nombre_usuario}", style_normal))
        elements.append(Spacer(1, 0.2 * inch))  # Espacio entre el nombre y la fecha

        elements.append(Paragraph(f"Fecha: {presupuesto['fecha'].strftime('%d/%m/%Y')}", style_normal))
        elements.append(Spacer(1, 0.2 * inch))  # Espacio entre la fecha y el detalle

        elements.append(Paragraph(f"Detalle: {presupuesto['detalle']}", style_normal))
        elements.append(Spacer(1, 0.2 * inch))  # Espacio entre el detalle y el costo total

        elements.append(Paragraph(f"Costo Total: ${presupuesto['costo']}", style_normal))

        # Construir el PDF
        doc.build(elements)

        # Mover el puntero al inicio del archivo
        buffer.seek(0)

        # Enviar el archivo PDF al cliente
        return send_file(buffer, as_attachment=True, download_name=f"Presupuesto_{presupuesto['codigo_presupuesto']}.pdf", mimetype='application/pdf')

    else:
        return "Presupuesto no encontrado", 404
    
def obtener_presupuesto_por_id(id_presupuesto):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Consulta para obtener el presupuesto por ID y el nombre del usuario
        cursor.execute('''
            SELECT p.*, u.nombre_completo_usuario 
            FROM Presupuestos p
            JOIN Usuarios u ON p.id_usuario = u.id_usuario
            WHERE p.id_presupuesto = %s
        ''', (id_presupuesto,))
        presupuesto = cursor.fetchone()
    except Exception as e:
        print(f"Error al obtener el presupuesto: {e}")
        presupuesto = None
    finally:
        cursor.close()
    
    return presupuesto

@app.route('/eliminar_presupuesto_admin/<int:id_presupuesto>', methods=['POST'])
def eliminar_presupuesto_admin(id_presupuesto):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para eliminar un presupuesto.', 'warning')
        return redirect(url_for('login_oficial'))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute('DELETE FROM Presupuestos WHERE id_presupuesto = %s', (id_presupuesto,))
        mysql.connection.commit()
        flash('Presupuesto eliminado exitosamente!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar el presupuesto: {e}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('ver_usuarios'))  # Redirige a la vista de usuarios

# Funcion para editar el usuario como administrador
@app.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
def editar_usuario(user_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para editar un usuario.', 'warning')
        return redirect(url_for('login_oficial'))
    
    # Comprobar si el usuario que se intenta editar es el admin
    if user_id == 1:  # Suponiendo que el ID del admin es 1
        flash('No se puede editar el usuario administrador.', 'danger')
        return redirect(url_for('ver_usuarios'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Obtener el usuario específico
    cursor.execute("SELECT * FROM usuarios WHERE id_usuario = %s", (user_id,))
    usuario = cursor.fetchone()

    if request.method == 'POST':
        nuevo_rol = request.form.get('rol')  # Solo se obtiene el rol

        # Validar que el rol no sea nulo
        if not nuevo_rol:
            flash('El rol no puede estar vacío.', 'danger')
            return redirect(url_for('ver_usuarios'))  # Volver a la página de usuarios

        try:
            # Actualizar el rol del usuario
            cursor.execute("UPDATE usuarios SET rol = %s WHERE id_usuario = %s", 
                           (nuevo_rol, user_id))
            mysql.connection.commit()
            flash('Rol de usuario editado correctamente.', 'success')
        except Exception as e:
            flash(f'Error al editar el rol del usuario: {str(e)}', 'danger')
            mysql.connection.rollback()

    cursor.close()
    return redirect(url_for('ver_usuarios'))



# Main
if __name__ == '__main__':
    app.run(debug=True)