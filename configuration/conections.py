import mysql


class DatabaseConnection:
    """Envoltura compatible con async que abre la conexión MySQL bajo demanda."""

    def __init__(self, host: str, user: str, password: str, database: str):
        """Guarda los parámetros de conexión para instanciar el conector cuando haga falta."""
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.mydb = None

    async def get_connection(self):
        """Devuelve la conexión MySQL reutilizable, creándola si aún no existe."""
        if self.mydb is None:
            self.mydb = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
        return self.mydb