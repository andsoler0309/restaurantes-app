from flask import request
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from flask_restful import Resource
import hashlib
from datetime import datetime
from sqlalchemy.orm import joinedload

from modelos import (
    db,
    Ingrediente,
    IngredienteSchema,
    RecetaIngrediente,
    RecetaIngredienteSchema,
    Receta,
    RecetaSchema,
    Usuario,
    UsuarioSchema,
    Restaurante,
    RestauranteSchema,
    Rol,
    MenuSemana,
    MenuSemanaSchema,
    MenuReceta,
)

ingrediente_schema = IngredienteSchema()
receta_ingrediente_schema = RecetaIngredienteSchema()
receta_schema = RecetaSchema()
usuario_schema = UsuarioSchema()
restaurante_schema = RestauranteSchema()
menu_semana_schema = MenuSemanaSchema()


class VistaSignIn(Resource):
    def post(self):
        usuario = Usuario.query.filter(
            Usuario.usuario == request.json["usuario"]
        ).first()
        if usuario is None:
            contrasena_encriptada = hashlib.md5(
                request.json["contrasena"].encode("utf-8")
            ).hexdigest()
            nuevo_usuario = Usuario(
                usuario=request.json["usuario"],
                contrasena=contrasena_encriptada,
                rol=Rol.ADMINISTRADOR,
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            token_de_acceso = create_access_token(identity=nuevo_usuario.id)
            return {"mensaje": "usuario creado exitosamente", "id": nuevo_usuario.id}
        else:
            return "El usuario ya existe", 404

    def put(self, id_usuario):
        usuario = Usuario.query.get_or_404(id_usuario)
        usuario.contrasena = request.json.get("contrasena", usuario.contrasena)
        db.session.commit()
        return usuario_schema.dump(usuario)

    def delete(self, id_usuario):
        usuario = Usuario.query.get_or_404(id_usuario)
        db.session.delete(usuario)
        db.session.commit()
        return "", 204


class VistaLogIn(Resource):
    def post(self):
        contrasena_encriptada = hashlib.md5(
            request.json["contrasena"].encode("utf-8")
        ).hexdigest()
        usuario = Usuario.query.filter(
            Usuario.usuario == request.json["usuario"],
            Usuario.contrasena == contrasena_encriptada,
        ).first()
        db.session.commit()
        print(str(hashlib.md5("admin".encode("utf-8")).hexdigest()))
        if usuario is None:
            return "El usuario no existe", 404
        else:
            token_de_acceso = create_access_token(identity=usuario.id)
            return {
                "mensaje": "Inicio de sesión exitoso",
                "token": token_de_acceso,
                "id": usuario.id,
                "rol": usuario.rol.value,
            }


class VistaIngredientes(Resource):
    @jwt_required()
    def get(self):
        ingredientes = Ingrediente.query.all()
        return [ingrediente_schema.dump(ingrediente) for ingrediente in ingredientes]

    @jwt_required()
    def post(self):
        nuevo_ingrediente = Ingrediente(
            nombre=request.json["nombre"],
            unidad=request.json["unidad"],
            costo=float(request.json["costo"]),
            calorias=float(request.json["calorias"]),
            sitio=request.json["sitio"],
        )

        db.session.add(nuevo_ingrediente)
        db.session.commit()
        return ingrediente_schema.dump(nuevo_ingrediente)


class VistaIngrediente(Resource):
    @jwt_required()
    def get(self, id_ingrediente):
        return ingrediente_schema.dump(Ingrediente.query.get_or_404(id_ingrediente))

    @jwt_required()
    def put(self, id_ingrediente):
        ingrediente = Ingrediente.query.get_or_404(id_ingrediente)
        ingrediente.nombre = request.json["nombre"]
        ingrediente.unidad = request.json["unidad"]
        ingrediente.costo = float(request.json["costo"])
        ingrediente.calorias = float(request.json["calorias"])
        ingrediente.sitio = request.json["sitio"]
        db.session.commit()
        return ingrediente_schema.dump(ingrediente)

    @jwt_required()
    def delete(self, id_ingrediente):
        ingrediente = Ingrediente.query.get_or_404(id_ingrediente)
        recetasIngrediente = RecetaIngrediente.query.filter_by(
            ingrediente=id_ingrediente
        ).all()
        if not recetasIngrediente:
            db.session.delete(ingrediente)
            db.session.commit()
            return "", 204
        else:
            return "El ingrediente se está usando en diferentes recetas", 409


class VistaRecetas(Resource):
    @jwt_required()
    def get(self, id_usuario):
        recetas = Receta.query.filter_by(usuario=str(id_usuario)).all()
        resultados = [receta_schema.dump(receta) for receta in recetas]
        ingredientes = Ingrediente.query.all()
        for receta in resultados:
            for receta_ingrediente in receta["ingredientes"]:
                self.actualizar_ingredientes_util(receta_ingrediente, ingredientes)

        return resultados

    @jwt_required()
    def post(self, id_usuario):
        nueva_receta = Receta(
            nombre=request.json["nombre"],
            preparacion=request.json["preparacion"],
            ingredientes=[],
            usuario=id_usuario,
            duracion=float(request.json["duracion"]),
            porcion=float(request.json["porcion"]),
        )
        for receta_ingrediente in request.json["ingredientes"]:
            nueva_receta_ingrediente = RecetaIngrediente(
                cantidad=receta_ingrediente["cantidad"],
                ingrediente=int(receta_ingrediente["idIngrediente"]),
            )
            nueva_receta.ingredientes.append(nueva_receta_ingrediente)

        db.session.add(nueva_receta)
        db.session.commit()
        return ingrediente_schema.dump(nueva_receta)

    def actualizar_ingredientes_util(self, receta_ingrediente, ingredientes):
        for ingrediente in ingredientes:
            if str(ingrediente.id) == receta_ingrediente["ingrediente"]:
                receta_ingrediente["ingrediente"] = ingrediente_schema.dump(ingrediente)
                receta_ingrediente["ingrediente"]["costo"] = float(
                    receta_ingrediente["ingrediente"]["costo"]
                )


class VistaReceta(Resource):
    @jwt_required()
    def get(self, id_receta):
        receta = Receta.query.get_or_404(id_receta)
        ingredientes = Ingrediente.query.all()
        resultados = receta_schema.dump(Receta.query.get_or_404(id_receta))
        recetaIngredientes = resultados["ingredientes"]
        for recetaIngrediente in recetaIngredientes:
            for ingrediente in ingredientes:
                if str(ingrediente.id) == recetaIngrediente["ingrediente"]:
                    recetaIngrediente["ingrediente"] = ingrediente_schema.dump(
                        ingrediente
                    )
                    recetaIngrediente["ingrediente"]["costo"] = float(
                        recetaIngrediente["ingrediente"]["costo"]
                    )

        return resultados

    @jwt_required()
    def put(self, id_receta):
        receta = Receta.query.get_or_404(id_receta)
        receta.nombre = request.json["nombre"]
        receta.preparacion = request.json["preparacion"]
        receta.duracion = float(request.json["duracion"])
        receta.porcion = float(request.json["porcion"])

        # Verificar los ingredientes que se borraron
        for receta_ingrediente in receta.ingredientes:
            borrar = self.borrar_ingrediente_util(
                request.json["ingredientes"], receta_ingrediente
            )

            if borrar == True:
                db.session.delete(receta_ingrediente)

        db.session.commit()

        for receta_ingrediente_editar in request.json["ingredientes"]:
            if receta_ingrediente_editar["id"] == "":
                # Es un nuevo ingrediente de la receta porque no tiene código
                nueva_receta_ingrediente = RecetaIngrediente(
                    cantidad=receta_ingrediente_editar["cantidad"],
                    ingrediente=int(receta_ingrediente_editar["idIngrediente"]),
                )
                receta.ingredientes.append(nueva_receta_ingrediente)
            else:
                # Se actualiza el ingrediente de la receta
                receta_ingrediente = self.actualizar_ingrediente_util(
                    receta.ingredientes, receta_ingrediente_editar
                )
                db.session.add(receta_ingrediente)

        db.session.add(receta)
        db.session.commit()
        return ingrediente_schema.dump(receta)

    @jwt_required()
    def delete(self, id_receta):
        receta = Receta.query.get_or_404(id_receta)
        db.session.delete(receta)
        db.session.commit()
        return "", 204

    def borrar_ingrediente_util(self, receta_ingredientes, receta_ingrediente):
        borrar = True
        for receta_ingrediente_editar in receta_ingredientes:
            if receta_ingrediente_editar["id"] != "":
                if int(receta_ingrediente_editar["id"]) == receta_ingrediente.id:
                    borrar = False

        return borrar

    def actualizar_ingrediente_util(
        self, receta_ingredientes, receta_ingrediente_editar
    ):
        receta_ingrediente_retornar = None
        for receta_ingrediente in receta_ingredientes:
            if int(receta_ingrediente_editar["id"]) == receta_ingrediente.id:
                receta_ingrediente.cantidad = receta_ingrediente_editar["cantidad"]
                receta_ingrediente.ingrediente = receta_ingrediente_editar[
                    "idIngrediente"
                ]
                receta_ingrediente_retornar = receta_ingrediente

        return receta_ingrediente_retornar


class VistaRestaurantes(Resource):
    @jwt_required()
    def post(self, id_usuario):
        usuario = Usuario.query.filter(Usuario.id == id_usuario).first()
        restaurante = Restaurante.query.filter(
            Restaurante.administrador_id == id_usuario
        ).filter(
            Restaurante.nombre == request.json["nombre"]
        ).first()

        if usuario is None:
            return "El Administrador no existe", 404
        elif usuario.rol != Rol.ADMINISTRADOR:
            return "Solo los Administradores pueden crear Restaurantes", 401
        elif restaurante is not None:
            
            return "Ya existe un restaurante con nombre: " + request.json["nombre"] + str(restaurante), 422

        else:
            nuevo_restaurante = Restaurante(
                nombre=request.json["nombre"],
                direccion=request.json["direccion"],
                telefono=request.json["telefono"],
                hora_atencion=request.json["hora_atencion"],
                facebook=request.json["facebook"],
                instagram=request.json["instagram"],
                twitter=request.json["twitter"],
                tipo_comida=request.json["tipo_comida"],
                is_en_lugar=request.json["is_en_lugar"],
                is_rappi=request.json["is_rappi"],
                is_didi=request.json["is_didi"],
                is_domicilios=request.json["is_domicilios"],
                administrador_id=id_usuario
            )

        db.session.add(nuevo_restaurante)
        db.session.commit()
        # TODO enviar el Schema como respuesta
        return {
            "mensaje": "Restaurante creado exitosamente",
            "id": nuevo_restaurante.id,
        }

    @jwt_required()
    def get(self, id_usuario):
        """
        Get all restaurants from an administrator

        :param id_usuario: id of the administrator
        :type id_usuario: int
        :return: list of restaurants
        :rtype: list
        """
        try:
            restaurantes = (
                Restaurante.query.filter_by(administrador_id=id_usuario)
                .order_by(Restaurante.nombre)
                .all()
            )
            return [
                restaurante_schema.dump(restaurante) for restaurante in restaurantes
            ]
        except SQLAlchemyError:
            error_message = "Error while querying the database"
            return {"error": error_message}, 500


class VistaMenuSemana(Resource):
    @jwt_required()
    def get(self):
        menus = MenuSemana.query.all()
        return [menu_semana_schema.dump(menu) for menu in menus]

    @jwt_required()
    def post(self,id_usuario):
        usuario = Usuario.query.filter(
            Usuario.id == id_usuario
        ).first()
        id_restaurante = None
        if usuario is None:
            return "El usuario no existe", 404
        if usuario.rol is Rol.CHEF:
            id_restaurante = usuario.restaurante_id
        else:
            id_restaurante = request.json["id_restaurante"]
        nombre_menu_repetido = MenuSemana.query.filter_by(
            nombre=request.json["nombre"]
        ).first()

        if nombre_menu_repetido is not None:
            return "El nombre del menu ya existe", 400
        try:
            fecha_inicial = datetime.strptime(
                request.json["fechaInicial"], "%Y-%m-%d"
            ).date()
            fecha_final = datetime.strptime(
                request.json["fechaFinal"], "%Y-%m-%d"
            ).date()
        except Exception as e:
            return str(e), 400

        diff_fecha = fecha_final - fecha_inicial
        if diff_fecha.days != 6:
            return "Las fechas no tienen la diferencia correcta", 400

        todos_menus = MenuSemana.query.all()
        for menu in todos_menus:
            if (fecha_final >= menu.fecha_final >= fecha_inicial) or (
                fecha_final >= menu.fecha_inicial >= fecha_inicial
            ):
                return "Las fechas tienen conflicto con las de otro menu", 400

        nuevo_menu_semana = MenuSemana(
            nombre=request.json["nombre"],
            fecha_inicial=fecha_inicial,
            fecha_final=fecha_final,
            id_restaurante=id_restaurante,
        )
        for receta_id in request.json["recetas"]:
            receta_menu = MenuReceta(menu=nuevo_menu_semana.id,receta=receta_id["id"])
            nuevo_menu_semana.recetas.append(receta_menu)
        db.session.add(nuevo_menu_semana)
        db.session.commit()
        return menu_semana_schema.dump(nuevo_menu_semana), 200

class VistaChef(Resource):
    @jwt_required()
    def post(self,id_usuario):
        usuario = Usuario.query.filter(Usuario.id == id_usuario).first()

        if usuario is None:
            return "El Administrador no existe", 404
        elif usuario.rol != Rol.ADMINISTRADOR:
            return "Solo los Administradores pueden crear Chef", 401
        
        usuario = Usuario.query.filter(
            Usuario.usuario == request.json["usuario"]
        ).first()
        if usuario is None:
            contrasena_encriptada = hashlib.md5(
                request.json["contrasena"].encode("utf-8")
            ).hexdigest()
            nuevo_usuario = Usuario(
                usuario=request.json["usuario"],
                contrasena=contrasena_encriptada,
                rol=Rol.CHEF,
                nombre = request.json["nombre"], 
                restaurante_id = request.json["restaurante_id"]
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            return {"mensaje": "chef creado exitosamente", "id": nuevo_usuario.id}
        else:
            return "El usuario ya existe", 404
