# A script that outputs a C++ wrapper for L3DT zeofuncs

import zeolite
import datetime
import os
import re
from string import Template

filename = 'zeofuncapi.c'

# substitute underscores for periods
def getFuncName(name):
    return re.sub('_', '.', name)
    
def typeToC(type):
    if (type == 'map'):
        return 'ZMAP'
    elif (type == 'string'):
        return 'const char *'
    elif (type == 'format'):
        return 'ZFORMAT'
    elif (type == 'varlist'):
        return 'ZLIST'
    elif (type == 'ZeoFunc'):
        return 'ZFUNC'
    elif (type == 'Climate'):
        return 'ZVAR' 
    elif (type == 'LandType'):
        return 'ZVAR' 
    elif (type == 'buffer'):
        return 'ZVAR'
    elif (type == 'colour'):
        return 'ZVAR'
    return type

def typeToConst(type):
    return 'VarID_' + type

def processItem(file,item,prefix):
    if (prefix != ''):
        prefix = prefix + '_'
    typeId = item.GetTypeID()
    if (typeId == zeolite.VarID_varlist):
        varlist = zeolite.CzList()
        varlist.Attach(item.GetZVAR())
        # branch
        x = 0
        while x < varlist.nItems():
            subitem = zeolite.CzVar(varlist.GetItem(x))
            processItem(file,subitem,prefix + item.GetName())
            x = x + 1
            
    if (typeId == zeolite.VarID_ZeoFunc):
        typename = zeolite.CzStr()
        arglist = zeolite.CzList()
        func = zeolite.CzFunc()
        func.Attach(item.GetZVAR())
        zeolite.cvar.theAPI.type_GetTypeName(func.GetReturnTypeID(), typename.GetZVAR());
        func.GetArgListPrototype(arglist.GetZVAR())
        argi = 0
        # the method return type and method name
        type = typename.GetText()
        file.write(typeToC(type) + ' ' + prefix + func.GetName() + ' (')
        
        # the method arguments
        while argi < arglist.nItems():
            temp = zeolite.CzVar(arglist.GetItem(argi))
            temp.GetTypeName(typename.GetZVAR())
            # the argument type and name
            type = typename.GetText()
            file.write(typeToC(type) + ' ' + temp.GetName())
            argi = argi + 1
            if (argi != arglist.nItems()):
                file.write(', ')
        file.write (')\n')
        argcode = ''
        if (arglist.nItems() == 0):
            code = Template(
'''{
    static ZFUNC hFunc$localname = NULL;
    
    if (hFunc$localname == NULL)
        hFunc$localname = theAPI.zeofunc_GetFunc("$name");

    ZVAR hRetVar = 0;
    bool bExecResult = theAPI.zeofunc_Execute2(hFunc$localname, NULL, &hRetVar);
    $returncode
}
''')
        else:
            code = Template(
'''{
    static ZFUNC hFunc$localname = NULL;
    
    if (hFunc$localname == NULL)
        hFunc$localname = theAPI.zeofunc_GetFunc("$name");

    ZLIST hArgs = theAPI.var_CreateTemp(VarID_varlist);
    $createallargs
    ZVAR hRetVar = 0;
    bool bExecResult = theAPI.zeofunc_Execute2(hFunc$localname, hArgs, &hRetVar);
    $returncode
}

''')
            argcode = '\n'
            argi = 0
            while argi < arglist.nItems():
                temp = zeolite.CzVar(arglist.GetItem(argi))
                temp.GetTypeName(typename.GetZVAR())
                # the argument type and name
                type = typename.GetText()

                createargt = ''
                # strings are a special case ...
                if (temp.GetTypeID() == zeolite.VarID_string):
                    createargt = Template(
'''
    ZVAR hVar$argname = theAPI.list_CreateItem(hArgs, $zeolitetype, "$argname");
    theAPI.str_SetText(hVar$argname, $argname);
''')
                elif (temp.GetTypeID() >= zeolite.VarID_colour and temp.GetTypeID() <= zeolite.VarID_ProgBox):
                # some vars are passed by reference
                    createargt = Template(
'''
    ZVAR hVar$argname = theAPI.list_CreateItem(hArgs, $zeolitetype, "$argname");
    theAPI.var_SetVarRef(hVar$argname, $argname);
''')
                else:
                # its a C atomic type, so pass a reference to it
                    createargt = Template(
'''
    ZVAR hVar$argname = theAPI.list_CreateItem(hArgs, $zeolitetype, "$argname");
    theAPI.var_SetValue(hVar$argname, &$argname);
''')
                
                argcode = argcode + createargt.substitute(
                            zeolitetype=typeToConst(type),
                            argname=temp.GetName()
                            )
                
                
                argi = argi + 1
        
        #return var
        returncodeg = ''
        if (func.GetReturnTypeID() != zeolite.VarID_void):
            returncodet = Template(
'''
    if (bExecResult)
    {
        $rettypename retValue;
        theAPI.var_GetValue(hRetVar, &retValue);
        return retValue;
    }
    return 0;
''')
            zeolite.cvar.theAPI.type_GetTypeName(func.GetReturnTypeID(), typename.GetZVAR());
            type = typename.GetText()
            returncodeg = returncodet.substitute(
                     rettypename=typeToC(type),
                     rettypenameconst=typeToConst(type)
                     )
        else:
            returncodeg = 'return;'
        codestr = code.substitute(
              localname=func.GetName(),
              name=getFuncName(prefix + func.GetName()),
              createallargs=argcode,
              returncode=returncodeg
              )
        file.write(codestr)
    return

getfunclist = zeolite.CzFunc()
if (getfunclist.GetFunc('zeofunc.GetFuncList') == False):
    print 'GetFunc failed for GetFuncList - this is serious...'

funclist = zeolite.CzList()
funclist.Attach(getfunclist.Execute())

header =   [ '/* THIS FILE IS AUTOMATICALLY GENERATED */\n',
                '/* ' + str(os.path.basename(__file__)) + ' ' + str(datetime.datetime.now()) + ' */\n\n' ]
file = open (filename, 'w')
file.writelines(header)

# Recursively loop through all the zeofuncs
i = 0
while i < funclist.nItems():
    var = zeolite.CzVar(funclist.GetItem(i))
    processItem(file,var,'')
    i = i + 1

footer = '/* EOF */\n\n'
file.writelines(footer)

file.close()

print filename + ' has been written'
