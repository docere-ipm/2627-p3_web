#!/bin/bash

# Mensaje de ayuda si no hay argumentos
if [ $# -eq 0 ]; then
    echo "Uso: $0 archivo1.html archivo2.css ..."
    exit 1
fi

# Recorrer todos los argumentos
for arg in "$@"; do
    case "$arg" in
        *.html)
            echo "---------------------- Procesando HTML: $arg"
            curl -H "Content-Type: text/html; charset=utf-8" \
                 --data-binary "@${arg}" \
  	         https://validator.w3.org/nu/?out=text
	    echo
            ;;
        *.css)
            echo "---------------------- Procesando CSS: $arg"
            curl -H "Content-Type: text/css; charset=utf-8" \
                 --data-binary "@${arg}" \
 	         https://validator.w3.org/nu/?out=text
	    echo
            ;;
        *)
            echo "---- Error: '$arg' no es un archivo .html ni .css." >&2
            echo
            continue
            ;;
    esac
	sleep 1
done
