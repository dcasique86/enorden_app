-- =====================================================
-- EnOrden - AppleScript Launcher
-- Ejecuta la aplicación sin mostrar terminal
-- =====================================================

property appPath : missing value

on run
    -- Obtener la ruta del script
    set appPath to POSIX path of (path to me)
    
    -- Si es un .app, obtener el directorio Contents/Resources
    if appPath ends with ".app/" then
        set scriptDir to do shell script "dirname " & quoted form of appPath & " | xargs dirname | xargs dirname"
        set scriptDir to scriptDir & "/Resources/"
    else
        -- Si es un .scpt, obtener el directorio donde está
        set scriptDir to do shell script "dirname " & quoted form of appPath
    end if
    
    -- Ejecutar el script de inicio en segundo plano
    do shell script "cd " & quoted form of scriptDir & " && chmod +x iniciar.sh && ./iniciar.sh > /dev/null 2>&1 &"
    
    -- Esperar un momento y mostrar mensaje
    delay 1
    display notification "EnOrden se está iniciando..." with title "EnOrden" sound name "Glass"
end run
