@app.route('/<name>/')
@app.route('/<name>')
def get_airfoil(name):
    airfoil = finder.airfoils.get(name, None)
    if airfoil:
        return jsonify({'airfoil': {'name': airfoil.name, 'ip': airfoil.ip}})
    else:
        return _error(name, f'No airfoil instance found with name \'{name}\'')