#!/usr/bin/env python3

import datetime as dt
from gettext import gettext as _
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Literal


DEBUG = True

class Error(Exception): pass

def is_error(value: object) -> bool:
    return isinstance(value, Error)


DATA_FILE = "baseline-data.json"


# Los 7 navegadores/plataformas exigidos por Baseline
CORE_BROWSERS = [
    "chrome",
    "chrome_android",
    "edge",
    "firefox",
    "firefox_android",
    "safari",
    "safari_ios",
]

# aprox. 30 meses
WIDELY_AVAILABLE_START_DATE = dt.datetime.now() - dt.timedelta(days= 913)


DEPRECATED = 'deprecated'
NO_STANDARD = 'no-standard'
LIMITED_AVAILABILITY = 'limited-availability'
NEWLY_AVAILABLE = 'newly-available'
WIDELY_AVAILABLE = 'widely-available'


type BaselineStatus = Literal[
    DEPRECATED, NO_STANDARD, LIMITED_AVAILABILITY,
    NEWLY_AVAILABLE, WIDELY_AVAILABLE,
]

class BCD: # Browser Compatibility Data
    @classmethod
    def load(cls: type, filename: str) -> Self:
        data = json.load(open(filename, mode= "r"))
        return cls(data)

    def __init__(self, data: dict):
        self.data = data

    def browser(self, name: str) -> dict | None:
        return self.data['browsers'].get(name, None)

    def browser_release_date(self, name: str, version: str) -> dt.datetime | None:
        browser = self.browser(name)
        release = browser['releases'].get(version, {})
        date_str = release.get('release_date')
        return dt.datetime.strptime(date_str, "%Y-%m-%d") if date_str else None

    def html_element(self, tagname: str) -> dict | None:
        return self.data['html']['elements'].get(tagname, None)

    def global_attribute(self, name: str) -> dict | None:
        return self.data['html']['global_attributes'].get(name, None)

    def css_property(self, name: str) -> dict | None:
        return self.data['css']['properties']
    
    def mdn_url(self, obj: dict) -> str:
        return obj['__compat']['mdn_url']

    def status(self, obj: dict) -> BaselineStatus | Error:
        compat = obj.get('__compat', None)
        if compat is None:
            return Error(_("no es un objeto con datos de compatibilidad: '{obj}'").format(obj= obj))
        status = compat.get('status', None)
        if status is None:
            return Error(_("__compat malformado, no tiene 'status': '{compat}'").format(compat = compat))
        if status['deprecated']:
            return DEPRECATED
        elif not status['standard_track']:
            return NO_STANDARD
        else:
            return self.calculate_baseline(compat['support'])
            
    def calculate_baseline(self, support: dict) -> BaselineStatus:
        widely_count = 0
        newly_count = 0
        for browser_name in CORE_BROWSERS:
            browser_support = support.get(browser_name, None)
            if browser_support is None:
                if DEBUG:
                    print(f"not supported: {browser_name}")
                continue
                
            version_added = self._get_version_added(browser_support)
            if version_added is None:
                if DEBUG:
                    print(f"no version added: {browser_name}")
                continue

            if version_added is True:
                widely_count = widely_count + 1
                continue

            release_date = self.browser_release_date(browser_name, version_added)
            if release_date is None:
                if DEBUG:
                    print(f"no release date: {browser_name}")
                continue
            
            if release_date > WIDELY_AVAILABLE_START_DATE:
                newly_count = newly_count + 1
            else:
                widely_count = widely_count + 1
        if widely_count == len(CORE_BROWSERS):
            return WIDELY_AVAILABLE
        elif newly_count + widely_count == len(CORE_BROWSERS):                
            return NEWLY_AVAILABLE
        else:
            return LIMITED_AVAILABILITY

        
    def _get_version_added(self, support_entry: dict) -> str | Literal[True] | None:
        entries = support_entry if isinstance(support_entry, list) else [support_entry]
        for item in entries:
            if (
                    item.get('flags')
                    or item.get('partial_implementation')
                    or item.get('version_removed')
                    or item.get('prefix')
                    or item.get('alternative_name')
            ):
                continue
            version = item.get('version_added')
            if version is True:
                return True
            
            if type(version) == str:
                return version.removeprefix("≤")
        return None
            
    
    def html_attr_status(self, tagname: str, attr: str, value: str) -> BaselineStatus | None:
        global_attr = self.global_attribute(attr)
        if global_attr is not None:
            return self.status(global_attr)
        else:
            element = self.html_element(tagname)
            status = set()
            tag_attr = element.get(attr, None)
            if tag_attr is not None:
                status.add(self.status(tag_attr))

            if value:
                if (obj := element.get(f"{attr}.{value}")):
                    status.add(self.status(obj))
                elif (obj := element.get(f"{attr}_{value}")):
                    status.add(self.status(obj))
                elif tag_attr is None:
                    return NO_STANDARD
                
            if status == {WIDELY_AVAILABLE}:
                return WIDELY_AVAILABLE

            elif status == {WIDELY_AVAILABLE, NEWLY_AVAILABLE} or status == {NEWLY_AVAILABLE}:
                return NEWLY_AVAILABLE

            elif status == {}:
                return NO_STANDARD
                
            else:
                return LIMITED_AVAILABILITY

                
def error(msg: str, **kwargs) -> None:
    print( msg.format(**kwargs), file= sys.stderr)


def check_html(bcd: BCD, code: str, only_widely_available: bool) -> int:
    error_count = 0
    parser = HTMLParser()

    def handle_starttag(tag: str, attrs: list[tuple]) -> None:
        nonlocal error_count
        nonlocal parser
        
        lineno, offset = parser.getpos()
         
        bcd_obj = bcd.html_element(tag)
        status = bcd.status(bcd_obj)
                                 
        if status is None:
            error(_("Línea {lineno}: '{tag}' no es un elemento html"),
                  tag= tag, lineno= lineno)
            error_count = error_count + 1
        
        if status == DEPRECATED:
            error(_("Línea {lineno}: '{tag}' está obsoleto, se desaconseja su uso\n  {mdn_url}"),
                       tag = tag, mdn_url= self.bcd.mdn_url(bcd_obj), lineno= lineno)
            error_count = error_count + 1
        
        elif status == NO_STANDARD:
            error(_("Línea {lineno}: '{tag}' no forma parte de ninguna especificación"),
                       tag= tag, lineno= lineno)
            error_count = error_count + 1
        
        elif status == LIMITED_AVAILABILITY:
            error(_("Línea {lineno}: '{tag}' no está en el baseline"),
                  tag= tag, lineno= lineno)
            error_count = error_count + 1
        
        elif status == NEWLY_AVAILABLE and only_widely_available:
            error(_("Línea {lineno}: '{tag}' sólo está newly available"),
                  tag= tag, lineno= lineno)
            error_count = error_count + 1
        
        for attr, value in attrs:
            status = bcd.html_attr_status(tag, attr, value)
            if status == DEPRECATED:
                error(_("Línea {lineno}: '{attr}' está obsoleto, se desaconseja su uso\n  {mdn_url}"),
                      attr = attr, mdn_url= self.bcd.tag_mdn_url(tag), lineno= lineno)
                error_count = error_count + 1
                
            elif status == NO_STANDARD:
                error(_("Línea {lineno}: '{attr}' no forma parte de ninguna especificación"),
                      attr= attr, lineno= lineno)
                error_count = error_count + 1

            elif status == LIMITED_AVAILABILITY:
                error(_("Línea {lineno}: '{attr}={value}' no está en el baseline"),
                      attr= attr, value= value, lineno= lineno)
                error_count = error_count + 1
                
            elif status == NEWLY_AVAILABLE and only_widely_available:
                error(_("Línea {lineno}: '{attr}={value}' sólo está newly available"),
                      attr= attr, value= value, lineno= lineno)
                error_count = error_count + 1
        
    parser.handle_starttag = handle_starttag
    parser.feed(code)
    return error_count


def check_css(bcd: BCD, code: str, only_widely_available: bool) -> int:
    error_count = 0
    no_comment = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Extraer propiedades CSS (ignorando custom properties --*)
    css_properties = re.findall(r"(?<![-\w])([a-zA-Z][a-zA-Z0-9-]*)\s*:", no_comment)
    for name in css_properties:
        bcd_obj = bcd.css_property(name)
        status = bcd.status(bcd_obj)
            
        if status is None:
            error(_("'{name}' no es una propiedad de CSS"), name= name)
            error_count = error_count + 1

        elif status == DEPRECATED:
            error(_("'{name}' está obsoleto, se desaconseja su uso\n  {mdn_url}"),
                  name= name, mdn_url= self.bcd.mdn_url(bcd_obj))
            error_count = error_count + 1


        elif status == NO_STANDARD:
            error(_("'{name}' no forma parte de ninguna especificación"),
                       name= name)
            error_count = error_count + 1

        elif status == LIMITED_AVAILABILITY:
            error(_("'{name}' no está en el baseline"), name= name)
            error_count = error_count + 1

        elif status == NEWLY_AVAILABLE and self.only_widely_available:
            error(_("'{name}' sólo está newly available"), name= name)
            error_count = error_count + 1
    
    return error_count


def main(filenames: list[str], only_widely_available: bool = True) -> None:
    data = json.load(open(DATA_FILE, mode= "r"))
    bcd = BCD(data)
    nivel = _("Widely Available") if only_widely_available else _("Newly/Widely Available")
    
    for filename in filenames:
        path = Path(filename).absolute()
        if not path.is_file():
            continue
        
        print(f"------------------------------------------ {filename}")
        try:
            with open(path, mode= "r") as f:
                texto = f.read()
        except UnicodeDecodeError as e:
            print(e)
            print()
            continue

        suffix = path.suffix.lower()
        if suffix == ".html":
            error_count = check_html(bcd, texto, only_widely_available)
            # checker = HTMLChecker(bcd)
            # checker.feed(texto)
            if error_count == 0:
                print(f"✅ Todos los elementos detectados cumplen 'Baseline ({nivel}).'")
            print()

        elif suffix == '.css':
            error_count = check_css(bcd, texto, only_widely_available)
            if error_count == 0:
                print(f"✅ Todos los elementos detectados cumplen 'Baseline ({nivel})'.")
            print()
                
        elif suffix == '.js':
            continue
            # Eliminar comentarios JS de línea y bloque
            sin_comentarios = re.sub(r"//.*?$|/\*.*?\*/", "", contenido, flags=re.DOTALL | re.MULTILINE)
            # Extraer llamadas a métodos/APIs tras punto (ej. .showModal, .animate)
            metodos = re.findall(r"\.([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(", sin_comentarios)
            identificadores_js.update(metodos)
            
            for metodo in sorted(metodos_js):
                # Buscar coincidencia en claves api.*.<metodo>
                coincidencias = [k for k in indice if k.startswith("api.") and k.endswith(f".{metodo}")]
                if coincidencias:
                    # Si todas las variantes de esa API están fuera de Baseline, avisar
                    estados = [indice[k]["baseline"] for k in coincidencias]
                    if not any(es_valido_baseline(e) for e in estados):
                        nombre = indice[coincidencias[0]]["nombre"]
                        alertas.append(f"[JS] '.{metodo}()' -> Estado Baseline: {estados[0]} ({nombre})")


        else:
            print("????")
        print()
        
    

if __name__ == "__main__":
    main(sys.argv[1:])


