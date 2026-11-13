"""
ExamForge Engine v3.0 - Layer 1: Specificity-First Parsing, Collision Assertions & Empirical Subtopic Extraction
Author: ExamForge Core Team
"""

import os
import re
import pandas as pd
from collections import defaultdict, Counter

def clean_qtext(text):
    if not isinstance(text, str):
        return ""
    t = text.strip()
    # 1. Truncate legacy KrutiDev Hindi text blocks
    hindi_legacy = re.search(r'([,\.]\s*e-\s*,-|,\s*e-\s*ih|Hkkx|uksV\s*%)', t)
    if hindi_legacy:
        t = t[:hindi_legacy.start()].strip()
    # 2. Truncate unicode Hindi
    hindi_match = re.search(r'[\u0900-\u097F]', t)
    if hindi_match:
        t = t[:hindi_match.start()].strip()
    # 3. Remove paper artifacts
    t = re.sub(r'\[\s*\d+\s*\]', ' ', t)
    t = re.sub(r'P\.\s*T\.\s*O\.', ' ', t, flags=re.I)
    t = re.sub(r'A[–-]\d+/[A-Za-z0-9–-]+', ' ', t)
    t = re.sub(r'B[–-]\d+/[A-Za-z0-9–-]+', ' ', t)
    t = re.sub(r'IGNOUAssignmentGuru\.com', ' ', t, flags=re.I)
    t = re.sub(r'MPA[-\s]*0?1[1-4]', ' ', t)
    t = re.sub(r'\b(20|10)\b', ' ', t)
    t = t.replace('“', ' ').replace('”', ' ').replace('‘', ' ').replace('’', ' ').replace("'", " ").replace('"', ' ')
    # 4. Fix OCR broken syllables
    t = re.sub(r'\bw\s+ork\b', 'work', t, flags=re.I)
    t = re.sub(r'\bsystem\s+s\b', 'systems', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# ------------------------------------------------------------------------------
# MPA-011 Specificity-First Classifier
# ------------------------------------------------------------------------------
def classify_mpa011(text, session="", qno=1):
    t = clean_qtext(text).lower()
    t_norm = re.sub(r'[-\s]+', ' ', t)
    
    # Unit 21: Ethics
    if any(k in t_norm for k in ['ethical', 'ethics', 'nolan', 'corruption', 'integrity in governance', 'accountability and ethics']):
        return 21
    # Unit 20: Conflict
    if any(k in t_norm for k in ['conflict', 'redefinition of conflict', 'dispute resolution', 'conflict resolution']):
        return 20
    # Unit 19: Civil Society
    if any(k in t_norm for k in ['civil society', 'ngo', 'voluntary organisation', 'voluntary action']):
        return 19
    # Unit 18: Governmental Institutions Reforms & Innovations (BPR, Judicial Reforms)
    if any(k in t_norm for k in ['business process reengineering', 'business process re engineering', 'bpr', 'governmental institutions', 'judicial system', 'judicial reform', 'administrative reforms commission', 'innovations in governance', 'political executive', 'revamping the political']):
        return 18
    # Unit 17: Good Governance
    if any(k in t_norm for k in ['good governance', 'world bank perspective of governance', 'pillars of good governance', 'initiatives towards good governance', 'good governance initiatives']):
        return 17
    # Unit 16: Emerging Concepts / NPM & Internationalisation of Public Governance
    if any(k in t_norm for k in ['internationalisation of public governance', 'internationalization of public governance', 'internationalisation of governance', 'internationalization of governance', 'new public management', 'npm', 'new public administration', 'new public service']):
        return 16
    # Unit 15: Challenges to Traditional Bureaucratic Paradigm
    if any(k in t_norm for k in ['traditional bureaucratic paradigm', 'challenges to weber', 'challenger to weber', 'critique of weberian', 'weber s concept of 10 bureaucracy', 'contemporary bureaucratic paradigm', 'contemporary bureaucratic approaches', 'state market relationship', 'state and market', 'state and the market', 'state - market - society', 'characteristics of bureaucratic administration']):
        return 15
    # Unit 14: Globalisation
    if any(k in t_norm for k in ['impact of globalisation on public administration', 'impact of globalisation on developing', 'impact of globalization on developing', 'impact of globalization on public administration', 'globalisation and administration', 'define iglobalisation', 'define globalisation', 'concept of globalisation', 'emerging challenges confronting public administra', 'globalisation manifests itself in the changing']):
        return 14
    # Unit 13: Indian Bureaucracy
    if any(k in t_norm for k in ['contemporary context of indian bureaucracy', 'indian bureaucracy', 'civil service in india', 'role of bureaucracy in india', 'major characteristics of weberian bureaucracy', 'weberian bureaucracy']):
        return 13
    # Unit 12: Role of Bureaucracy in Policy
    if any(k in t_norm for k in ['policy implementation', 'policy formulation', 'policy analysis', 'bureaucracy in policy', 'public policy', 'policy complementation']):
        return 12
    # Unit 11: Changing Nature of Indian State
    if any(k in t_norm for k in ['nature of the indian state', 'issues confront the state in india', 'indian state']):
        return 11
    # Unit 10: Social Participation, Gender, Environment, Applied Social Justice
    if any(k in t_norm for k in ['applied aspects of social justice', 'gender', 'environment', 'social participation', 'engendering public administration']):
        return 10
    # Unit 9: Social Equity, Participation, Autonomy
    if any(k in t_norm for k in ['social justice', 'social equity', 'social equality', 'participation, autonomy', 'autonomy and flexibility', 'marginalised groups', 'norms of participation', 'participation in the governance']):
        return 9
    # Unit 8: Democratic People's Struggles
    if any(k in t_norm for k in ['chilka', 'people s struggle', 'struggles for public', 'democratic struggle', 'peoples struggle', 'peoples struggle']):
        return 8
    # Unit 7: Citizen-Administration Interface & RTI
    if any(k in t_norm for k in ['interface between citizen', 'citizen administration', 'citizen and administration', 'right to information', 'citizen s charter', 'citizens charter', 'citizens charter', 'institutional strategies and devices for building citizen', 'institutional devices and strategies for citizens']):
        return 7
    # Unit 6: Gandhian Perspective
    if any(k in t_norm for k in ['gandhian', 'gandhi', 'sarvodaya', 'swaraj', 'trusteeship']):
        return 6
    # Unit 5: Neo-Liberal Perspective
    if any(k in t_norm for k in ['neo liberal', 'neoliberal', 'milton friedman', 'hayek', 'nozick']):
        return 5
    # Unit 4: Liberal and Marxist Perspective
    if any(k in t_norm for k in ['liberal and marxist', 'marxian perspective', 'marxist perspective', 'liberal perspective', 'liberalism represents']):
        return 4
    # Unit 3: Changing Role of the State
    if any(k in t_norm for k in ['changing role of the state', 'role of the state in the globalisation', 'role of state in the context of globalisation', 'role of the state in the context of globalisation', 'role of state in the globalisation', 'slate and discuss its role in the globalisation']):
        return 3
    # Unit 2: State, Society and Public Administration
    if any(k in t_norm for k in ['state society and public administration', 'society admin', 'society administration', 'society and public administration', 'societal culture', 'prismatic', 'riggs', 'closely related to society', 'weberian contribution to society', 'concepts of society state and public administration', 'concepts of society, state and public administration']):
        return 2
    # Unit 1: Nature of the State
    if any(k in t_norm for k in ['nature of the state', 'nature of modern state', 'emergence of modern state', 'perspectives of the state', 'changing perspectives on the nature', 'changing perspectives of the state', 'changing perspective of the nature', 'define the state', 'concept of state', 'no consensus on any definition of the state', 'evolution of the state']):
        return 1

    # Text fallbacks
    if 'globalisation' in t_norm or 'globalization' in t_norm:
        return 3 if qno <= 5 else 14
    if 'bureaucracy' in t_norm or 'bureaucratic' in t_norm:
        return 2 if qno <= 5 else 12

    return 1 if qno <= 5 else 14

# ------------------------------------------------------------------------------
# MPA-012 Specificity-First Classifier
# ------------------------------------------------------------------------------
def classify_mpa012(text, session="", qno=1):
    t = clean_qtext(text).lower()
    t_norm = re.sub(r'[-\s]+', ' ', t)
    
    # 1. Socio-Psychological Thinkers (Units 11, 12, 13)
    if any(k in t_norm for k in ['herzberg', 'maslow', 'need hierarchy', 'hierarchy of needs', 'two factor', 'hygiene', 'prepotency', 'self actualisation', 'self actualization', 'human motivation']):
        return 12
    if any(k in t_norm for k in ['mcgregor', 'vroom', 'theory x', 'theory y', 'expectancy theory', 'assumptions underlying theory']):
        return 13
    if any(k in t_norm for k in ['chris argyris', 'argyris', 'immaturity maturity', 'human personality']):
        return 11

    # 2. Decision Making - Simon (Unit 9)
    if any(k in t_norm for k in ['herbert simon', 'herbert a. simon', 'bounded rationality', 'satisficing', 'proverbs of administration', 'fact value', 'rational decision making', 'decision making']):
        return 9

    # 3. Human Relations - Mayo (Unit 8)
    if any(k in t_norm for k in ['elton mayo', 'hawthorne', 'human relations', 'western electric', 'illumination experiment', 'bank wiring', 'worker morale']):
        return 8

    # 4. Classical & Bureaucratic (Units 4, 5, 6, 7)
    if any(k in t_norm for k in ['scientific management', 'f.w. taylor', 'taylor', 'functional foremanship', 'mental revolution', 'time and motion']):
        return 4
    if any(k in t_norm for k in ['henri fayol', 'fayol', 'gulick', 'urwick', 'mooney', 'reiley', 'posdcorb', 'principles of delegation', 'general principles of administration', 'principles of administrative management', 'principles of an organization', 'major principles of an organization', 'major principles of organisation', 'principles of public administration', 'principles of organisation']):
        return 5
    if any(k in t_norm for k in ['ideal type bureaucracy', 'legal rational', 'types of authority', 'weberian', 'max weber', 'weber']):
        if any(k in t_norm for k in ['critique', 'dysfunction', 'marx', 'patholog', 'lenin', 'stalin']):
            return 7
        return 6
    if any(k in t_norm for k in ['critique of bureaucracy', 'pathologies of bureaucracy', 'merton', 'gouldner', 'selznick', 'peter blau', 'dysfunctions of bureaucracy', 'marx s views on bureaucracy', 'marxian paradigm of bureaucracy', 'views of karl marx, lenin']):
        return 7

    # 5. Systems & Modern Org Theories (Units 14, 15, 16, 17)
    if any(k in t_norm for k in ['chester barnard', 'chester bernard', 'david easton', 'barnard', 'bernard', 'zone of indifference', 'acceptance theory', 'functions of the executive', 'input output', 'views of chester i. bernard', 'views of chester i. barnard', 'david easton s views on systems']):
        return 15
    if any(k in t_norm for k in ['closed and open systems', 'open and closed systems', 'open systems approach', 'open and cooperative systems']):
        return 14
    if any(k in t_norm for k in ['systems approach to the study of organisation', 'systems approach to organisation']):
        return 14
    if any(k in t_norm for k in ['peter senge', 'learning organisation', 'learning organization', 'five disciplines', 'learning disabilities']):
        return 16
    if any(k in t_norm for k in ['organisational culture', 'organizational culture']):
        return 17
    if any(k in t_norm for k in ['open systems', 'cooperative systems', 'homeostasis', 'negative entropy', 'equifinality', 'boundary spanning']):
        return 14

    # 6. Contemporary Approaches (Units 18, 19, 20, 21, 22)
    if any(k in t_norm for k in ['public choice', 'niskanen', 'tullock', 'ostrom', 'bureaucratic monopoly', 'budget maximisation', 'polycentric', 'rent seeking', 'functioning of bureau']):
        return 19
    if any(k in t_norm for k in ['critical theory', 'habermas', 'frankfurt school', 'communicative action', 'instrumental reason']):
        return 20
    if any(k in t_norm for k in ['new public management', 'npm', 'reinventing government', 'managerialism', 'osborne', 'gaebler', 'contracting out']):
        return 21
    if any(k in t_norm for k in ['new public administration', 'minnowbrook', 'npa', 'waldo', 'anti goals', 'goals and anti goals', 'social equity']):
        return 18
    if any(k in t_norm for k in ['state of administrative theory', 'changing nature of public service', 'new public service', 'collaborative governance', 'digital era governance', '21st century', 'public value', 'recent trends in management of organisation', 'recent trends in the management of organisations', 'recent trends in management of organisations']):
        return 22

    # 7. Block 1: Foundations & Evolution (Units 1, 2, 3) and Unit 10
    if any(k in t_norm for k in ['theory building', 'growth of administrative theory', 'administrative theory has grown', 'development and growth', 'characteristics of administrative theory', 'importance of public administration theory', 'evolution and growth of administrative theory']):
        return 3
    if any(k in t_norm for k in ['typology of organisations', 'typologies of organisation', 'typologies of an organiza', 'formal and informal organisation', 'principles and significance of organisation']):
        return 2
    if any(k in t_norm for k in ['organisational structure', 'leadership', 'control in organisation', 'communication in organisation', 'models of organisational influence', 'characteristics of an organization', 'characteristics of organisation', 'concept and characteristics of an organisation', 'concept of organisation and its characteristics', 'classified by some scholars based on size']):
        return 10
    if any(k in t_norm for k in ['meaning, nature, scope', 'meaning nature and scope', 'public and private administration', 'distinguish it from private administration', 'liberalisation, privatisation and globalisation', 'lpg', 'importance of public administration', 'define public administration', 'administration is the organisation and use of men']):
        return 1

    # Heuristic guards
    if 'organisation' in t_norm or 'organization' in t_norm:
        return 2 if qno <= 5 else 17
    if 'theory' in t_norm:
        return 3 if qno <= 5 else 20
    return 1 if qno <= 5 else 21

# ------------------------------------------------------------------------------
# MPA-013 Specificity-First Classifier
# ------------------------------------------------------------------------------
def classify_mpa013(text, session="", qno=1):
    t = clean_qtext(text).lower()
    t_norm = re.sub(r'[-\s]+', ' ', t)
    
    # 1. Block 6: Units 23, 24, 25
    if any(k in t_norm for k in ['dysfunctionalities of public system', 'dysfunctionalitie', 'maladies of public systems', 'maladies', 'four pronged strategy', 'continuity and change in public systems', 'globalisation and public systems reforms']):
        return 25
    if any(k in t_norm for k in ['empowerment', 'notion of empowerment', 'marginalised', 'marginalisation', 'women and development', 'paradigm shift in development strategy']):
        return 24
    if any(k in t_norm for k in ['reforms and change management', 'change management', 'administrative reforms', 'administrative reform in india', 'models of change management', 'approaches to change', 'organisational development']):
        return 23

    # 2. Block 5: Units 19, 20, 21, 22
    if any(k in t_norm for k in ['networking and inter institutional', 'network society', 'concept of network', 'networking', 'inter institutional coordination']):
        return 22
    if any(k in t_norm for k in ['transparency and right to information', 'right to information', 'r ight to information', 'transparency in governance']):
        return 21
    if any(k in t_norm for k in ['responsiveness mechanisms', 'responsiveness in public system', 'responsiveness', 'citizens charter and responsiveness']):
        return 20
    if any(k in t_norm for k in ['accountability', 'types of accountability', 'perspectives of accountability', 'accountability under good governance']):
        return 19

    # 3. Block 4: Units 15, 16, 17, 18
    if any(k in t_norm for k in ['group decision making', 'group decision', 'nominal group technique', 'decision making techniques', 'trend extrapolation', 'delphi technique', 'delphi', 'future designing techniques', 'forecasting techniques']):
        return 18
    if any(k in t_norm for k in ['selective market techniques', 'contracting out', 'outsourcing in public', 'market techniques for improving efficiency']):
        return 17
    if any(k in t_norm for k in ['work measurement', 'work management techniques', 'essentials of work measurement', 'analytical estimating', 'time study', 'work sampling', 'techniques of work measurement']):
        return 16
    if any(k in t_norm for k in ['information systems', 'information system', 'management information system', 'mis in public', 'types of information']):
        return 15

    # 4. Block 3: Units 11, 12, 13, 14
    if any(k in t_norm for k in ['systems analysis', 'system s analysis', 'phases of systems analysis', 'phase s of system s analysis', 'approaches of systems analysis', 'key management tools', 'total quality management', 'tqm']):
        return 14
    if any(k in t_norm for k in ['project management', 'life cycle of project management', 'strategic management', 'strategic planning', 'phases of strategic management', 'process of strategic management', 'schools of thought in strategic management', 'strategic management in public and private']):
        return 13
    if any(k in t_norm for k in ['inventory control', 'abc analysis', 'always better control', 'materials management', 'logistics management', 'techniques of inventory control']):
        return 12
    if any(k in t_norm for k in ['financial management', 'budget', 'budgeting', 'approaches to budgeting', 'legislation of the budget', 'auditing of accounts', 'parliamentary scrutiny', 'public accounts committee', 'estimates committee', 'parliament in controlling receipts and expenditure', 'pac']):
        return 11

    # 5. Block 2: Units 7, 8, 9, 10
    if any(k in t_norm for k in ['inter governmental relations', 'inter governmental relationship', 'models of inter governmental', 'intergovernmental relations', 'inter governmental']):
        return 10
    if any(k in t_norm for k in ['legislature', 'judiciary', 'judicial activitism', 'judicial activism', 'public interest litigation', 'pil', 'e judiciary']):
        return 9
    if any(k in t_norm for k in ['bureaucracy and political executive', 'political executive in governance', 'civil service and minister', 'role of bureaucracy in governance']):
        return 8
    if any(k in t_norm for k in ['concept of governance', 'models of governance', 'contextual uses of governance', 'governance is used in several contexts', 'forms of governance', 'governance an introduction']):
        return 7

    # 6. Block 1: Units 2, 3, 4, 5, 6
    if any(k in t_norm for k in ['new technologies', 'sachivalaya vahini', 'ict in public', 'e governance', 'technological transformation']):
        return 6
    if any(k in t_norm for k in ['constitutional environment', 'constitutional context', 'constitutional authorities', 'citizens rights']):
        return 3
    if any(k in t_norm for k in ['political context', 'new managerialism', 'rise of new managerialism', 'regulatory state', 'role of the regulatory state', 'changing nature of state and economy']):
        return 4
    if any(k in t_norm for k in ['socio economic context', 'environment of public systems', 'socio economic environment', 'economic factors affect the nature', 'social context of public systems', 'social context of public system']):
        return 5
    if any(k in t_norm for k in ['changing nature of the public service', 'changing nature of public service', 'distinctiveness of public systems', 'distinguish between bureaucratic sys', 'distinguish it from the bureaucratic', 'public systems management and bureaucratic']):
        return 2

    # 7. Unit 1: Foundations
    if any(k in t_norm for k in ['concept of public systems management', 'concept of public system s management', 'nature and scope of public systems', 'characteristics of public systems', 'theoretical foundations of evolution of public systems', 'theoretical foundation s of evolution of the concept', 'scope of public systems management']):
        return 1

    # Broad fallback
    if 'governance' in t_norm:
        return 7
    if 'technology' in t_norm:
        return 6
    if 'bureaucra' in t_norm:
        return 8
    if 'management' in t_norm:
        return 13 if qno > 5 else 2

    return 1 if qno <= 5 else 23

# ------------------------------------------------------------------------------
# MPA-014 Specificity-First Classifier
# ------------------------------------------------------------------------------
def classify_mpa014(text, session="", qno=1):
    pid = str(session)
    t = clean_qtext(text).lower()
    t_norm = re.sub(r'[-\s]+', ' ', t)
    
    # Specific per-paper collision resolutions
    if pid == 'MPA014_2015_DEC' and qno == 3:
        return 8 # Promotion as reward and career recognition
    if pid == 'MPA014_2016_DEC' and qno == 8:
        return 17 # Grievance committee / employee involvement
    if pid == 'MPA014_2019_JUN' and qno == 8:
        return 3 # Recruitment planning
    if pid == 'MPA014_2020_JUN' and qno == 6:
        return 6 # Performance Appraisal & Merit Assessment
    if pid == 'MPA014_2012_JUN' and qno == 8:
        return 17 # Employee dissatisfaction / involvement
    if pid == 'MPA014_2023_DEC' and qno == 8:
        return 18 # Industrial Peace under Industrial Relations
    if pid == 'MPA014_2023_JUN' and qno == 10:
        return 17 # Conflict resolution via employee consultation
    if pid == 'MPA014_2015_JUN' and qno == 3:
        return 5 # Ascertaining merit in recruitment
    if pid == 'MPA014_2022_JUN' and qno == 5:
        return 5 # Ascertaining merit

    # Block 6: Units 20, 21, 22, 23
    if any(k in t_norm for k in ['stress management', 'manage stress', 'approache4 to stress management', 'ancient indian', 'burnout', 'occupational stress']):
        return 23
    if any(k in t_norm for k in ['managing change', 'organisational change', 'introducing change', 'change in organisation', 'approaches to change', 'change at the work place', 'resistance to change in hrm', 'management of goals and actions for introducing change']):
        return 22
    if any(k in t_norm for k in ['human resource information systems', 'information systems in hrm', 'human resource audit', 'hr audit', 'hr auditing', 'human resource accounting', 'hra']):
        return 21
    if any(k in t_norm for k in ['assessing the effectiveness', 'assessing human resource', 'evaluating human resource effectiveness', 'hrm effectiveness', 'effectiveness of human resource', 'effectiveness of human relations', 'four c s model', 'effectiveness standards']):
        return 20

    # Block 5: Units 16, 17, 18, 19
    if any(k in t_norm for k in ['domestic enquiry', 'disciplinary procedures', 'discipline and grievances', 'aspects of discipline', 'discipline in civil service', 'discipline']):
        return 19
    if any(k in t_norm for k in ['collective bargaining', 'trade unions', 'trade unionism', 'dispute resolution in industry', 'labour policy', 'features of labour policy', 'articulation of labour policy', 'industrial relations', 'role of technology in industrial relations', 'grievance handling machinery', 'grievance machinery']):
        return 18
    if any(k in t_norm for k in ['industrial peace', 'industrial harmony', 'features of industrial peace', 'concept of industrial peace', 'employee involvement', 'employment involvement', 'workers participation', 'worker s participation', 'wpm', 'quality circles', 'quality circle', 'empowerment in hrm']):
        return 17
    if any(k in t_norm for k in ['health', 'employee health', 'employees health', 'occupational health', 'employee safety', 'health and safety']):
        return 16

    # Block 4: Units 10, 11, 12, 13, 14, 15
    if any(k in t_norm for k in ['total quality management', 'tqm in hrm', 'deming']):
        return 15
    if any(k in t_norm for k in ['capacity building', 'employee capacity']):
        return 14
    if any(k in t_norm for k in ['management development', 'mdp', 'considerations for effective management development']):
        return 13
    if any(k in t_norm for k in ['learning and teaching', 'teaching process', 'learning and development', 'learning process', 'experiential learning', 'adult learning', 'andragogy']):
        return 12
    if any(k in t_norm for k in ['voluntary retirement scheme', 'vrs', 're skill', 'reskill', 'reskilling', 'redeployment and reskilling', 'redeployment']):
        return 11
    if any(k in t_norm for k in ['training principles', 'methods of training', 'training and development', 'training need', 'tni', 'kirkpatrick', 'training cycle']):
        return 10

    # Block 3: Units 6, 7, 8, 9
    if any(k in t_norm for k in ['pension scheme', 'pension', 'employee benefits', 'employees benefits', 'fringe benefits', 'types of employee benefits', 'types of employees benefits', 'social security']):
        return 9
    if any(k in t_norm for k in ['rewards and incentive', 'incentive plans', 'incentive plan', 'incentives', 'material and non material incentive', 'motivation and incentives', 'promotion is an effective tool of recognition']):
        return 8
    if any(k in t_norm for k in ['remuneration', 'salary system', 'salary structure', 'salary scales', 'wages and salary', 'wage policy', 'job evaluation', 'pay commission', 'principles of remuneration']):
        return 7
    if any(k in t_norm for k in ['management by objectives', 'mbo', 'performance appraisal', 'performance management', 'performance rating', '360 degree']):
        return 6

    # Block 2: Units 3, 4, 5
    if any(k in t_norm for k in ['recruitment process', 'methods of recruitment', 'what is recruitment', 'public service commission', 'upsc', 'ascertaining merit in recruitment']):
        return 5
    if any(k in t_norm for k in ['promotion system', 'essentials of promotion', 'principles of promotion', 'promotion plays an important role', 'what is promotion', 'promotion']):
        return 5
    if any(k in t_norm for k in ['ascertaining merit', 'ascertain merit', 'merit can be ascertained', 'merit is ascertained', 'steps in recruitment']):
        return 5
    if any(k in t_norm for k in ['job analysis', 'job design', 'job enlargement', 'job enrichment', 'job description', 'job specification']):
        return 4
    if any(k in t_norm for k in ['manpower planning', 'man power planning', 'human resource planning', 'hr planning', 'process of manpower planning', 'requirements of manpower planning']):
        return 3

    # Block 1: Units 1, 2
    if any(k in t_norm for k in ['strategic human resource', 'strategic hrm', 'shrm', 'idea of strategic', 'concepts of strategy']):
        return 2
    if any(k in t_norm for k in ['human resource development and its characteristics', 'meaning, nature, scope and significance', 'human resource management and discuss its characteristics', 'objectives and scope of human resource', 'soft and hard versions', 'significance of human resource management', 'define human resource management', 'evolution of human resource management', 'personnel management and human resource', 'human resource management and discuss its objectives', 'features of human resource management', 'scope of human resource management']):
        return 1

    # Fallbacks
    if 'training' in t_norm:
        return 10
    if 'recruitment' in t_norm:
        return 5
    if 'strategic' in t_norm:
        return 2
    return 1 if qno <= 5 else 18


# ------------------------------------------------------------------------------
# Empirical Subtopic Extractor (PYQ Stem Clustering)
# ------------------------------------------------------------------------------
def extract_empirical_subtopics(df, unit_col='unit_id', text_col='clean_text', top_n=4):
    """
    Extracts authentic IGNOU syllabus subtopics by clustering actual historical PYQ stems
    for each unit, eliminating external LLM hallucinations.
    """
    unit_stems = defaultdict(list)
    for _, row in df.iterrows():
        u = row[unit_col]
        txt = clean_qtext(str(row[text_col]))
        if txt:
            unit_stems[u].append(txt)

    subtopics = {}
    stop_words = {'discuss', 'explain', 'examine', 'analyse', 'analyze', 'describe', 'highlight',
                  'elucidate', 'comment', 'briefly', 'note', 'what', 'critical', 'critically',
                  'bring', 'light', 'short', 'notes', 'words', 'each', 'marks', 'view', 'views'}

    for u, texts in unit_stems.items():
        # Clean phrases
        phrases = []
        for t in texts:
            # extract key clause
            t_clean = re.sub(r'^(discuss|explain|examine|analyse|analyze|describe|highlight|elucidate|write a note on)\s+', '', t, flags=re.I)
            t_clean = re.sub(r'\s+(discuss|explain|examine|comment|elucidate)\.?$', '', t_clean, flags=re.I)
            phrases.append(t_clean.strip())

        # Select representative distinct stems
        distinct_stems = []
        for p in phrases:
            if p and len(p) > 12:
                # check overlap
                if not any(p[:20].lower() in existing.lower() for existing in distinct_stems):
                    distinct_stems.append(p)
            if len(distinct_stems) >= top_n:
                break
        
        # If fewer than top_n, pad with cleaned phrases
        for p in phrases:
            if len(distinct_stems) >= top_n:
                break
            if p not in distinct_stems and len(p) > 8:
                distinct_stems.append(p)

        subtopics[u] = distinct_stems[:top_n]

    return subtopics
