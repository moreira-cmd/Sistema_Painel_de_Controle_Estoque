from flask import Flask
from database import init_db
from routes import main 

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # PDFs de até 10 MB
app.secret_key = "Repositorio-de-Moreira"
app.register_blueprint(main)

if __name__ == '__main__':
    init_db()  # Inicializa o banco de dados (cria tabelas e estruturas necessárias)
    app.run(debug=True)