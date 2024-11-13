/*
==================================================
  Multi Baterías - Base de Datos 
  Desarrollado por: Harry, Ingeniero Informático de la Universidad Tecnológica Metropolitana del Estado de Chile.
  Fecha: Noviembre, 04, 2024.
==================================================
*/

-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS Multibaterias;

-- Usar la base de datos creada
USE Multibaterias;

-- Tabla del Formulario de Contacto
CREATE TABLE IF NOT EXISTS Contacto (
    id_contacto INT AUTO_INCREMENT PRIMARY KEY,             -- ID único
    nombre_contacto VARCHAR(255) NOT NULL,                  -- Nombre del contacto
    correo_contacto VARCHAR(255) NOT NULL,                  -- Correo electrónico del contacto
    sexo CHAR(1) NOT NULL CHECK (sexo IN ('M', 'F')),        -- Sexo del contacto ('M' para masculino, 'F' para femenino)
    asunto TEXT NOT NULL,                                   -- Asunto del mensaje
    fecha_contacto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,      -- Fecha y hora del contacto
	archivado BOOLEAN DEFAULT FALSE                         -- Indica si el contacto está archivado
);
drop table contacto;
select * from contacto;
ALTER TABLE Contacto
ADD COLUMN respuesta TEXT;  -- Campo para almacenar la respuesta del administrador



-- Verificar que se ha creado correctamente la tabla de contacto
SELECT * FROM Contacto;

-- Tabla de Usuarios
CREATE TABLE IF NOT EXISTS Usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,               -- ID único del usuario
    username VARCHAR(50) NOT NULL UNIQUE,                    -- Nombre de usuario (único)
    password VARCHAR(255) NOT NULL,                          -- Contraseña del usuario (encriptada en la práctica)
    email_usuario VARCHAR(255) NOT NULL UNIQUE,              -- Correo electrónico (único)
    rol ENUM('usuario', 'admin') DEFAULT 'usuario',          -- Rol del usuario: 'usuario' o 'admin'
    nombre_completo_usuario VARCHAR(255) NOT NULL,           -- Nombre completo del usuario
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP       -- Fecha de creación del usuario
);

-- Insertar un usuario con rol 'admin'
INSERT INTO Usuarios (username, password, email_usuario, rol, nombre_completo_usuario)
VALUES ('admin_multibaterias', 'multibaterias4033', 'multibateriasmaipuss@gmail.com', 'admin', 'Administrador Principal');

-- Insertar usuarios de prueba con rol 'usuario'
INSERT INTO Usuarios (username, password, email_usuario, rol, nombre_completo_usuario)
VALUES 
('Jarol Riquelme', 'JarolSe9.', 'jriquelme@utem.cl', 'usuario', 'Jarol Riquelme Santibañez'),
('Bastian Basso', 'bastian123', 'bbasso@utem.cl', 'usuario', 'Bastian Basso xD');

-- Verificar que se ha creado correctamente la tabla de usuarios y que el admin está registrado
SELECT * FROM Usuarios;

-- Consultar el rol del usuario 'admin_multibaterias'
SELECT username, rol 
FROM Usuarios 
WHERE username = 'admin_multibaterias' AND password = 'multibaterias4033';




-- Tabla de mis horas agendadas --
CREATE TABLE IF NOT EXISTS citas (
    id_cita INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,                            -- ID del usuario (clave foránea)
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_citas FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)  -- Clave foránea
);

select * from citas;

SELECT * FROM citas WHERE id_cita = '1';

-- Tabla de Presupuestos
CREATE TABLE IF NOT EXISTS Presupuestos (
    id_presupuesto INT AUTO_INCREMENT PRIMARY KEY,          -- ID único del presupuesto
    id_usuario INT NOT NULL,                                -- ID del usuario (clave foránea)
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,              -- Fecha de creación del presupuesto
    codigo_presupuesto VARCHAR(20) NOT NULL UNIQUE,         -- Código único del presupuesto
    detalle TEXT NOT NULL,                                  -- Detalle del presupuesto
    costo DECIMAL(10, 2) NOT NULL,                          -- Costo del servicio
    CONSTRAINT fk_usuario_presupuestos FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario)  -- Clave foránea
);

ALTER TABLE citas ADD COLUMN id_presupuesto INT;

ALTER TABLE citas 
ADD CONSTRAINT fk_presupuesto_citas 
FOREIGN KEY (id_presupuesto) REFERENCES Presupuestos(id_presupuesto);






