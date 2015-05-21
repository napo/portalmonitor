__author__ = 'jumbrich'

from urlparse import urlparse
import urlnorm
from datetime import datetime
import sys
import requests.exceptions
import exceptions

def computeID(url):
    up = urlparse(urlnorm.norm(url))
    return up.hostname

# The mappings
nameorgs = {
    # New top level domains as described by ICANN
    # http://www.icann.org/tlds/
    "aero": "air-transport industry",
    "arpa": "Arpanet",
    "biz": "business",
    "com": "commercial",
    "coop": "cooperatives",
    "edu": "educational",
    "gov": "government",
    "info": "unrestricted `info'",
    "int": "international",
    "mil": "military",
    "museum": "museums",
    "name": "`name' (for registration by individuals)",
    "net": "networking",
    "org": "non-commercial",
    "pro": "professionals",
    # These additional ccTLDs are included here even though they are not part
    # of ISO 3166.  IANA has 5 reserved ccTLDs as described here:
    #
    # http://www.iso.org/iso/en/prods-services/iso3166ma/04background-on-iso-3166/iso3166-1-and-ccTLDs.html
    #
    # but I can't find an official list anywhere.
    #
    # Note that `uk' is the common practice country code for the United
    # Kingdom.  AFAICT, the official `gb' code is routinely ignored!
    #
    # <D.M.Pick@qmw.ac.uk> tells me that `uk' was long in use before ISO3166
    # was adopted for top-level DNS zone names (although in the reverse order
    # like uk.ac.qmw) and was carried forward (with the reversal) to avoid a
    # large-scale renaming process as the UK switched from their old `Coloured
    # Book' protocols over X.25 to Internet protocols over IP.
    #
    # See <url:ftp://ftp.ripe.net/ripe/docs/ripe-159.txt>
    #
    # Also, `su', while obsolete is still in limited use.
    "ac": "Ascension Island",
    "gg": "Guernsey",
    "im": "Isle of Man",
    "je": "Jersey",
    "uk": "United Kingdom (common practice)",
    "su": "Soviet Union (still in limited use)",
}

countries = {
    "af": "Afghanistan",
    "al": "Albania",
    "dz": "Algeria",
    "as": "American Samoa",
    "ad": "Andorra",
    "ao": "Angola",
    "ai": "Anguilla",
    "aq": "Antarctica",
    "ag": "Antigua and Barbuda",
    "ar": "Argentina",
    "am": "Armenia",
    "aw": "Aruba",
    "au": "Australia",
    "at": "Austria",
    "az": "Azerbaijan",
    "bs": "Bahamas",
    "bh": "Bahrain",
    "bd": "Bangladesh",
    "bb": "Barbados",
    "by": "Belarus",
    "be": "Belgium",
    "bz": "Belize",
    "bj": "Benin",
    "bm": "Bermuda",
    "bt": "Bhutan",
    "bo": "Bolivia",
    "ba": "Bosnia and Herzegowina",
    "bw": "Botswana",
    "bv": "Bouvet Island",
    "br": "Brazil",
    "io": "British Indian Ocean Territory",
    "bn": "Brunei Darussalam",
    "bg": "Bulgaria",
    "bf": "Burkina Faso",
    "bi": "Burundi",
    "kh": "Cambodia",
    "cm": "Cameroon",
    "ca": "Canada",
    "cv": "Cape Verde",
    "ky": "Cayman Islands",
    "cf": "Central African Republic",
    "td": "Chad",
    "cl": "Chile",
    "cn": "China",
    "cx": "Christmas Island",
    "cc": "Cocos (Keeling) Islands",
    "co": "Colombia",
    "km": "Comoros",
    "cg": "Congo",
    "cd": "Congo, The Democratic Republic of the",
    "ck": "Cook Islands",
    "cr": "Costa Rica",
    "ci": "Cote D'Ivoire",
    "hr": "Croatia",
    "cu": "Cuba",
    "cy": "Cyprus",
    "cz": "Czech Republic",
    "dk": "Denmark",
    "dj": "Djibouti",
    "dm": "Dominica",
    "do": "Dominican Republic",
    "tp": "East Timor",
    "ec": "Ecuador",
    "eg": "Egypt",
    "sv": "El Salvador",
    "gq": "Equatorial Guinea",
    "er": "Eritrea",
    "ee": "Estonia",
    "et": "Ethiopia",
    "fk": "Falkland Islands (Malvinas)",
    "fo": "Faroe Islands",
    "fj": "Fiji",
    "fi": "Finland",
    "fr": "France",
    "gf": "French Guiana",
    "pf": "French Polynesia",
    "tf": "French Southern Territories",
    "ga": "Gabon",
    "gm": "Gambia",
    "ge": "Georgia",
    "de": "Germany",
    "gh": "Ghana",
    "gi": "Gibraltar",
    "gr": "Greece",
    "gl": "Greenland",
    "gd": "Grenada",
    "gp": "Guadeloupe",
    "gu": "Guam",
    "gt": "Guatemala",
    "gn": "Guinea",
    "gw": "Guinea-Bissau",
    "gy": "Guyana",
    "ht": "Haiti",
    "hm": "Heard Island and Mcdonald Islands",
    "va": "Holy See (Vatican City State)",
    "hn": "Honduras",
    "hk": "Hong Kong",
    "hu": "Hungary",
    "is": "Iceland",
    "in": "India",
    "id": "Indonesia",
    "ir": "Iran, Islamic Republic of",
    "iq": "Iraq",
    "ie": "Ireland",
    "il": "Israel",
    "it": "Italy",
    "jm": "Jamaica",
    "jp": "Japan",
    "jo": "Jordan",
    "kz": "Kazakstan",
    "ke": "Kenya",
    "ki": "Kiribati",
    "kp": "Korea, Democratic People's Republic of",
    "kr": "Korea, Republic of",
    "kw": "Kuwait",
    "kg": "Kyrgyzstan",
    "la": "Lao People's Democratic Republic",
    "lv": "Latvia",
    "lb": "Lebanon",
    "ls": "Lesotho",
    "lr": "Liberia",
    "ly": "Libyan Arab Jamahiriya",
    "li": "Liechtenstein",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "mo": "Macau",
    "mk": "Macedonia, The Former Yugoslav Republic of",
    "mg": "Madagascar",
    "mw": "Malawi",
    "my": "Malaysia",
    "mv": "Maldives",
    "ml": "Mali",
    "mt": "Malta",
    "mh": "Marshall Islands",
    "mq": "Martinique",
    "mr": "Mauritania",
    "mu": "Mauritius",
    "yt": "Mayotte",
    "mx": "Mexico",
    "fm": "Micronesia, Federated States of",
    "md": "Moldova, Republic of",
    "mc": "Monaco",
    "mn": "Mongolia",
    "ms": "Montserrat",
    "ma": "Morocco",
    "mz": "Mozambique",
    "mm": "Myanmar",
    "na": "Namibia",
    "nr": "Nauru",
    "np": "Nepal",
    "nl": "Netherlands",
    "an": "Netherlands Antilles",
    "nc": "New Caledonia",
    "nz": "New Zealand",
    "ni": "Nicaragua",
    "ne": "Niger",
    "ng": "Nigeria",
    "nu": "Niue",
    "nf": "Norfolk Island",
    "mp": "Northern Mariana Islands",
    "no": "Norway",
    "om": "Oman",
    "pk": "Pakistan",
    "pw": "Palau",
    "ps": "Palestinian Territory, Occupied",
    "pa": "Panama",
    "pg": "Papua New Guinea",
    "py": "Paraguay",
    "pe": "Peru",
    "ph": "Philippines",
    "pn": "Pitcairn",
    "pl": "Poland",
    "pt": "Portugal",
    "pr": "Puerto Rico",
    "qa": "Qatar",
    "re": "Reunion",
    "ro": "Romania",
    "ru": "Russian Federation",
    "rw": "Rwanda",
    "sh": "Saint Helena",
    "kn": "Saint Kitts and Nevis",
    "lc": "Saint Lucia",
    "pm": "Saint Pierre and Miquelon",
    "vc": "Saint Vincent and the Grenadines",
    "ws": "Samoa",
    "sm": "San Marino",
    "st": "Sao Tome and Principe",
    "sa": "Saudi Arabia",
    "sn": "Senegal",
    "sc": "Seychelles",
    "sl": "Sierra Leone",
    "sg": "Singapore",
    "sk": "Slovakia",
    "si": "Slovenia",
    "sb": "Solomon Islands",
    "so": "Somalia",
    "za": "South Africa",
    "gs": "South Georgia and the South Sandwich Islands",
    "es": "Spain",
    "lk": "Sri Lanka",
    "sd": "Sudan",
    "sr": "Suriname",
    "sj": "Svalbard and Jan Mayen",
    "sz": "Swaziland",
    "se": "Sweden",
    "ch": "Switzerland",
    "sy": "Syrian Arab Republic",
    "tw": "Taiwan, Province of China",
    "tj": "Tajikistan",
    "tz": "Tanzania, United Republic of",
    "th": "Thailand",
    "tg": "Togo",
    "tk": "Tokelau",
    "to": "Tonga",
    "tt": "Trinidad and Tobago",
    "tn": "Tunisia",
    "tr": "Turkey",
    "tm": "Turkmenistan",
    "tc": "Turks and Caicos Islands",
    "tv": "Tuvalu",
    "ug": "Uganda",
    "ua": "Ukraine",
    "ae": "United Arab Emirates",
    "gb": "United Kingdom",
    "us": "United States",
    "um": "United States Minor Outlying Islands",
    "uy": "Uruguay",
    "uz": "Uzbekistan",
    "vu": "Vanuatu",
    "ve": "Venezuela",
    "vn": "Viet Nam",
    "vg": "Virgin Islands, British",
    "vi": "Virgin Islands, U.S.",
    "wf": "Wallis and Futuna",
    "eh": "Western Sahara",
    "ye": "Yemen",
    "yu": "Yugoslavia",
    "zm": "Zambia",
    "zw": "Zimbabwe",
}

all = nameorgs.copy()
all.update(countries)


def getCountry(url):

	url_elements = urlparse(url).netloc.split(".")

	tld = ".".join(url_elements[-2:])
	if tld in all:
		return all[tld]
	elif url_elements[-1] in all:
		return all[url_elements[-1]]
	else:
		return "unknown"


def getExceptionCode(e):

    #connection erorrs
    if isinstance(e,requests.exceptions.ConnectionError):
        return 702
    if isinstance(e,requests.exceptions.ConnectTimeout):
        return 703
    if isinstance(e,requests.exceptions.ReadTimeout):
        return 704
    if isinstance(e,requests.exceptions.HTTPError):
        return 705
    if isinstance(e,requests.exceptions.TooManyRedirects):
        return 706
    if isinstance(e,requests.exceptions.Timeout):
        return 707
    if isinstance(e,requests.exceptions.RetryError):
        return 708

    #parser errors
    if isinstance(e, exceptions.ValueError):
        return 801

    #format errors
    if isinstance(e,urlnorm.InvalidUrl):
        return 901
    if isinstance(e,requests.exceptions.InvalidSchema):
        return 902
    if isinstance(e,requests.exceptions.MissingSchema):
        return 903

    else:
        return 600


def getSnapshot(args):
    if args.snapshot:
        return args.snapshot
    else:
        now = datetime.now()
        y=now.isocalendar()[0]
        w=now.isocalendar()[1]
        sn=str(y)+'-'+str(w)
        if not args.ignore:
            while True:
                choice = raw_input("WARNING: Do you really want to use the current date as snapshot "+sn+"?: (Y/N)").lower()
                if choice == 'y':
                    break
                elif choice == 'n':
                    return None
                else:
                    sys.stdout.write("Please respond with 'y' or 'n' \n")
        return sn


def analyseStatus(statusmap, status):
    sstr=str(status)
    if sstr[0]=='2':
        statusmap['ok']+=1
    elif sstr[0]=='4':
        statusmap['offline']+=1
    elif sstr[0]=='5':
        statusmap['serverErr']+=1
    elif sstr[0]=='7':
        statusmap['connErr']+=1
    elif sstr[0]=='8':
        statusmap['parserErr']+=1
    elif sstr[0]=='9':
        statusmap['formatErr']+=1
    statusmap['count']+=1

def initStatusMap():
    return {
        'count':0,
        'ok':0,
        'offline':0,
        'serverErr':0,
        'connErr':0,
        'parserErr':0,
        'formatErr':0
    }


def extractMimeType( ct):
    if ";" in ct:
        return str(ct)[:ct.find(";")].strip()
    return ct.strip()

def head(url, redirects=0, props=None):
    if not props:
        props={}
    headResp = requests.head(url=url,timeout=(1, 10.0))#con, read -timeout

    header_dict = dict((k.lower(), v) for k, v in dict(headResp.headers).iteritems())
    props['size']=header_dict['content-length']
    props['mime']=extractMimeType(header_dict['content-type'])
    props['status']=headResp.status_code
    props['header']=header_dict

    if headResp.status_code == requests.codes.moved:
        moved_url = header_dict['location']
        if redirects == 0:
            props['redirects']=[]
        props['redirects'].append(header_dict)
        if redirects < 3:
            redirects += 1
            return head(url=moved_url, redirects=redirects,props=props)
        else:
            props['status']=777
    return props
