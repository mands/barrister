
inproc_registry = { }

class RpcException(Exception):
    pass

class InProcState(object):

    def __init__(self):
        self.server = None

class InProcTransport(object):

    def __init__(self, name, validate_request=True, validate_response=True):
        self.validate_req  = validate_request
        self.validate_resp = validate_response
        self.name = name
        if not inproc_registry.has_key(name):
            inproc_registry[name] = InProcState()
        self.state = inproc_registry[name]

    def serve(self, server):
        self.state.server = server

    def client(self):
        if self.state.server:
            return Client(self, self.state.server.contract)
        else:
            raise RpcException("No server bound to InProcTransport '%s'" % self.name)

    def call(self, iface_name, func_name, params):
        if self.state.server:
            self._validate_request(iface_name, func_name, params)
            resp = self.state.server.call(iface_name, func_name, params)
            self._validate_response(iface_name, func_name, resp)
            return resp
        else:
            raise RpcException("No server bound to InProcTransport '%s'" % self.name)

    def _validate_request(self, iface_name, func_name, params):
        if self.validate_req:
            self.state.server.contract.validate_request(iface_name, func_name, params)

    def _validate_response(self, iface_name, func_name, resp):
        if self.validate_resp:
            self.state.server.contract.validate_response(iface_name, func_name, resp)

class Server(object):

    def __init__(self, contract):
        self.contract = contract
        self.handlers = { }

    def set_interface_handler(self, name, handler):
        self.handlers[name] = handler

    def call(self, iface_name, func_name, params):
        if self.handlers.has_key(iface_name):
            iface_impl = self.handlers[iface_name]
            func = getattr(iface_impl, func_name)
            if func:
                if params:
                    return func(*params)
                else:
                    return func()
            else:
                msg = "Function '%s.%s' not found" % (iface_name, func_name)
                raise RpcException(msg)
        else:
            msg = "No implementation of '%s' found" % (iface_name)
            raise RpcException(msg)        

class Client(object):
    
    def __init__(self, transport, contract):
        self.transport = transport
        self.contract = contract
        for k, v in self.contract.interfaces.items():
            setattr(self, k, InterfaceClientProxy(transport, v))

class InterfaceClientProxy(object):

    def __init__(self, transport, iface):
        iface_name = iface.name
        for func_name, func in iface.functions.items():
            setattr(self, func_name, self._caller(transport, iface_name, func_name))

    def _caller(self, transport, iface_name, func_name):
        return lambda *params: transport.call(iface_name, func_name, params)

class Contract(object):

    def __init__(self, idl_parsed):
        self.idl_parsed = idl_parsed
        self.interfaces = { }
        self.structs = { }
        self.enums = { }
        for e in idl_parsed:
            if e["type"] == "struct":
                self.structs[e["name"]] = e
            elif e["type"] == "enum":
                self.enums[e["name"]] = e
            elif e["type"] == "interface":
                self.interfaces[e["name"]] = Interface(e, self)

    def validate_request(self, iface_name, func_name, params):
        self.interface(iface_name).function(func_name).validate_params(params)

    def validate_response(self, iface_name, func_name, resp):
        self.interface(iface_name).function(func_name).validate_response(resp)

    def interface(self, iface_name):
        if self.interfaces.has_key(iface_name):
            return self.interfaces[iface_name]
        else:
            raise RpcException("Unknown interface: '%s'", iface_name)

class Interface(object):

    def __init__(self, iface, contract):
        self.name = iface["name"]
        self.functions = { }
        for f in iface["functions"]:
            self.functions[f["name"]] = Function(self.name, f, contract)

    def function(self, func_name):
        if self.functions.has_key(func_name):
            return self.functions[func_name]
        else:
            raise RpcException("%s: Unknown function: '%s'", self.name, func_name)

class Function(object):

    def __init__(self, iface_name, f, contract):
        self.name = f["name"]
        self.params = f["params"]
        self.returns = f["returns"]
        self.full_name = "%s.%s" % (iface_name, self.name)
        
    def validate_params(self, params):
        if len(self.params) != len(params):
            vals = (self.full_name, len(self.params), len(params))
            raise RpcException("Function '%s' expects %d param(s). %d given." % vals)
        for p in self.params:
            pass

    def validate_response(self, resp):
        pass
