from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileScenario:
    key: str
    label: str
    profile_text: str
    roles: str
    skills: str
    locations: str
    experience_level: str
    work_modes: str = ""


VALIDATION_PROFILES: tuple[ProfileScenario, ...] = (
    ProfileScenario(
        key="comptable_junior",
        label="Comptable junior",
        profile_text=(
            "Role: Comptable junior. Skills: comptabilite, MS Office, gestion, audit, fiscalite, francais. "
            "Experience: junior, 1 a 2 ans. Location: Tunis or Ariana. Education: CCA or Bac+3."
        ),
        roles="Comptable",
        skills="comptabilite,MS Office,gestion,audit,fiscalite,francais",
        locations="Tunis,Ariana",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="comptable_confirme",
        label="Comptable confirme",
        profile_text=(
            "Role: Comptable confirme. Skills: comptabilite generale, fiscalite, declarations, paie, Excel, "
            "rapprochement bancaire. Experience: confirme, 3 a 5 ans. Location: Tunis or Ariana. Education: Bac+3."
        ),
        roles="Comptable,Comptable confirme,Comptable general",
        skills="comptabilite generale,fiscalite,declarations,paie,Excel,rapprochement bancaire",
        locations="Tunis,Ariana",
        experience_level="CONFIRME",
    ),
    ProfileScenario(
        key="production_team_lead",
        label="Chef d'equipe production",
        profile_text=(
            "Role: Chef d'equipe production. Skills: controle qualite, tracabilite, process industriel, "
            "production agroalimentaire, organisation, gestion equipe. Experience: confirme, 2 a 4 ans. "
            "Location: Ben Arous. Education: Bac+3. Work mode: on-site."
        ),
        roles="Chef d'equipe production",
        skills="controle qualite,tracabilite,process industriel,production agroalimentaire,organisation,gestion equipe",
        locations="Ben Arous",
        experience_level="CONFIRME",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="civil_engineer_junior",
        label="Ingenieur genie civil travaux",
        profile_text=(
            "Role: Ingenieur genie civil travaux. Skills: Autocad, MS Project, controle qualite, planning chantier, "
            "supervision travaux, etudes de terrain. Experience: junior, 1 a 3 ans. Location: Ben Arous or Tunis. "
            "Education: Bac+5. Work mode: on-site."
        ),
        roles="Ingenieur genie civil travaux",
        skills="Autocad,MS Project,controle qualite,planning chantier,supervision travaux,etudes de terrain",
        locations="Ben Arous,Tunis",
        experience_level="JUNIOR",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="civil_engineer_senior",
        label="Ingenieur genie civil senior",
        profile_text=(
            "Role: Ingenieur genie civil senior. Skills: conduite travaux, coordination chantier, planning, "
            "Autocad, MS Project, management equipe. Experience: senior, 6 a 10 ans. Location: Tunis or Sfax."
        ),
        roles="Ingenieur genie civil,Chef projet genie civil,Conducteur travaux",
        skills="conduite travaux,coordination chantier,planning,Autocad,MS Project,management equipe",
        locations="Tunis,Sfax",
        experience_level="SENIOR",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="it_helpdesk",
        label="IT Helpdesk Officer",
        profile_text=(
            "Role: IT Helpdesk Officer. Skills: support helpdesk, Windows, Microsoft 365, Active Directory, reseau, "
            "installation hardware software, troubleshooting. Experience: junior, 1 a 3 ans. Location: Tunis. "
            "Education: Bac+3."
        ),
        roles="IT Helpdesk Officer,Support IT,Technicien support informatique",
        skills="support helpdesk,Windows,Microsoft 365,Active Directory,reseau,installation hardware software,troubleshooting",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="backend_django",
        label="Backend Django developer",
        profile_text=(
            "Role: Backend Django Developer. Skills: Python, Django, REST API, PostgreSQL, Docker, Git, tests. "
            "Experience: junior to confirme, 1 a 4 ans. Location: Tunis or remote."
        ),
        roles="Backend Developer,Django Developer,Python Developer",
        skills="Python,Django,REST API,PostgreSQL,Docker,Git,tests",
        locations="Tunis,Ariana",
        experience_level="JUNIOR",
        work_modes="REMOTE,HYBRID,ON_SITE",
    ),
    ProfileScenario(
        key="frontend_react_junior",
        label="Frontend React junior",
        profile_text=(
            "Role: Frontend React Developer. Skills: React, JavaScript, TypeScript, HTML, CSS, Tailwind, API integration. "
            "Experience: junior, 0 a 2 ans. Location: Tunis or Ariana."
        ),
        roles="Frontend Developer,React Developer,Developpeur Frontend",
        skills="React,JavaScript,TypeScript,HTML,CSS,Tailwind,API integration",
        locations="Tunis,Ariana",
        experience_level="JUNIOR",
        work_modes="REMOTE,HYBRID,ON_SITE",
    ),
    ProfileScenario(
        key="fullstack_js",
        label="Fullstack JavaScript",
        profile_text=(
            "Role: Fullstack JavaScript Developer. Skills: Node.js, React, Express, SQL, MongoDB, Git, Docker. "
            "Experience: confirme, 3 a 5 ans. Location: Tunis."
        ),
        roles="Fullstack Developer,JavaScript Developer,Node.js Developer",
        skills="Node.js,React,Express,SQL,MongoDB,Git,Docker",
        locations="Tunis",
        experience_level="CONFIRME",
        work_modes="REMOTE,HYBRID,ON_SITE",
    ),
    ProfileScenario(
        key="data_analyst",
        label="Data analyst",
        profile_text=(
            "Role: Data Analyst. Skills: SQL, Python, Excel, Power BI, dashboards, reporting, data cleaning. "
            "Experience: junior, 1 a 3 ans. Location: Tunis."
        ),
        roles="Data Analyst,Business Intelligence Analyst,BI Analyst",
        skills="SQL,Python,Excel,Power BI,dashboards,reporting,data cleaning",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="digital_marketing",
        label="Charge marketing digital",
        profile_text=(
            "Role: Charge marketing digital. Skills: SEO, SEA, social media, Facebook Ads, Google Ads, content, analytics. "
            "Experience: junior, 1 a 3 ans. Location: Tunis."
        ),
        roles="Charge marketing digital,Digital Marketing Specialist,Community Manager",
        skills="SEO,SEA,social media,Facebook Ads,Google Ads,content,analytics",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="sales_representative",
        label="Commercial terrain",
        profile_text=(
            "Role: Commercial terrain. Skills: prospection, negociation, vente B2B, portefeuille client, CRM, reporting. "
            "Experience: confirme, 2 a 5 ans. Location: Tunis or Sousse."
        ),
        roles="Commercial,Sales Representative,Charge commercial",
        skills="prospection,negociation,vente B2B,portefeuille client,CRM,reporting",
        locations="Tunis,Sousse",
        experience_level="CONFIRME",
    ),
    ProfileScenario(
        key="customer_support",
        label="Conseiller support client",
        profile_text=(
            "Role: Conseiller support client. Skills: appels entrants, email, chat, resolution problemes, CRM, francais. "
            "Experience: debutant a junior, 0 a 2 ans. Location: Tunis."
        ),
        roles="Conseiller client,Customer Support,Teleconseiller",
        skills="appels entrants,email,chat,resolution problemes,CRM,francais",
        locations="Tunis",
        experience_level="DEBUTANT",
    ),
    ProfileScenario(
        key="hr_assistant",
        label="Assistant RH",
        profile_text=(
            "Role: Assistant RH. Skills: recrutement, administration personnel, paie, entretiens, sourcing, Excel. "
            "Experience: junior, 1 a 3 ans. Location: Tunis."
        ),
        roles="Assistant RH,Charge RH,Assistant ressources humaines",
        skills="recrutement,administration personnel,paie,entretiens,sourcing,Excel",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="finance_analyst",
        label="Analyste financier",
        profile_text=(
            "Role: Analyste financier. Skills: analyse financiere, reporting, Excel avance, budget, forecast, Power BI. "
            "Experience: junior, 1 a 3 ans. Location: Tunis."
        ),
        roles="Analyste financier,Financial Analyst,Controleur de gestion junior",
        skills="analyse financiere,reporting,Excel avance,budget,forecast,Power BI",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="logistics_coordinator",
        label="Coordinateur logistique",
        profile_text=(
            "Role: Coordinateur logistique. Skills: supply chain, transport, stock, planning, ERP, coordination fournisseurs. "
            "Experience: confirme, 2 a 5 ans. Location: Ben Arous or Tunis."
        ),
        roles="Coordinateur logistique,Logistics Coordinator,Agent logistique",
        skills="supply chain,transport,stock,planning,ERP,coordination fournisseurs",
        locations="Ben Arous,Tunis",
        experience_level="CONFIRME",
    ),
    ProfileScenario(
        key="maintenance_technician",
        label="Technicien maintenance",
        profile_text=(
            "Role: Technicien maintenance industrielle. Skills: maintenance preventive, electricite, mecanique, diagnostic, GMAO. "
            "Experience: junior to confirme, 1 a 4 ans. Location: Ben Arous."
        ),
        roles="Technicien maintenance,Technicien maintenance industrielle",
        skills="maintenance preventive,electricite,mecanique,diagnostic,GMAO",
        locations="Ben Arous",
        experience_level="JUNIOR",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="quality_controller",
        label="Controleur qualite",
        profile_text=(
            "Role: Controleur qualite. Skills: controle qualite, procedures qualite, normes, audit, reporting, Excel. "
            "Experience: junior, 1 a 3 ans. Location: Ben Arous."
        ),
        roles="Controleur qualite,Technicien qualite",
        skills="controle qualite,procedures qualite,normes,audit,reporting,Excel",
        locations="Ben Arous",
        experience_level="JUNIOR",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="nurse",
        label="Infirmier",
        profile_text=(
            "Role: Infirmier. Skills: soins infirmiers, urgence, suivi patient, hygiene, dossier medical. "
            "Experience: junior, 1 a 3 ans. Location: Tunis or Sousse."
        ),
        roles="Infirmier,Infirmiere,Nurse",
        skills="soins infirmiers,urgence,suivi patient,hygiene,dossier medical",
        locations="Tunis,Sousse",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="graphic_designer",
        label="Graphic designer",
        profile_text=(
            "Role: Graphic Designer. Skills: Adobe Photoshop, Illustrator, branding, social media design, print, Canva. "
            "Experience: junior, 1 a 3 ans. Location: Tunis or remote."
        ),
        roles="Graphic Designer,Designer graphique,Infographiste",
        skills="Adobe Photoshop,Illustrator,branding,social media design,print,Canva",
        locations="Tunis",
        experience_level="JUNIOR",
        work_modes="REMOTE,HYBRID,ON_SITE",
    ),
    ProfileScenario(
        key="project_manager",
        label="Chef de projet",
        profile_text=(
            "Role: Chef de projet. Skills: coordination equipe, planning, budget, reporting, gestion risques, communication. "
            "Experience: senior, 5 a 8 ans. Location: Tunis."
        ),
        roles="Chef de projet,Project Manager",
        skills="coordination equipe,planning,budget,reporting,gestion risques,communication",
        locations="Tunis",
        experience_level="SENIOR",
    ),
    ProfileScenario(
        key="admin_assistant",
        label="Assistant administratif",
        profile_text=(
            "Role: Assistant administratif. Skills: gestion administrative, accueil, classement, courrier, Excel, facturation. "
            "Experience: debutant a junior, 0 a 2 ans. Location: Tunis."
        ),
        roles="Assistant administratif,Assistant de direction,Secretaire",
        skills="gestion administrative,accueil,classement,courrier,Excel,facturation",
        locations="Tunis",
        experience_level="DEBUTANT",
    ),
    ProfileScenario(
        key="procurement_buyer",
        label="Acheteur",
        profile_text=(
            "Role: Acheteur. Skills: achats, sourcing fournisseurs, negociation, appels d'offres, ERP, suivi commandes. "
            "Experience: confirme, 2 a 5 ans. Location: Tunis or Ben Arous."
        ),
        roles="Acheteur,Procurement Officer,Responsable achats junior",
        skills="achats,sourcing fournisseurs,negociation,appels d'offres,ERP,suivi commandes",
        locations="Tunis,Ben Arous",
        experience_level="CONFIRME",
    ),
    ProfileScenario(
        key="legal_assistant",
        label="Assistant juridique",
        profile_text=(
            "Role: Assistant juridique. Skills: contrats, veille juridique, droit des societes, classement dossiers, francais. "
            "Experience: junior, 1 a 3 ans. Location: Tunis."
        ),
        roles="Assistant juridique,Juriste junior,Legal Assistant",
        skills="contrats,veille juridique,droit des societes,classement dossiers,francais",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="devops_junior",
        label="DevOps junior",
        profile_text=(
            "Role: DevOps junior. Skills: Linux, Docker, CI/CD, GitLab, monitoring, cloud basics, scripting. "
            "Experience: junior, 1 a 3 ans. Location: Tunis or remote."
        ),
        roles="DevOps Engineer,DevOps junior,System Administrator",
        skills="Linux,Docker,CI/CD,GitLab,monitoring,cloud basics,scripting",
        locations="Tunis",
        experience_level="JUNIOR",
        work_modes="REMOTE,HYBRID,ON_SITE",
    ),
)


def scenario_options(scenario: ProfileScenario) -> dict[str, Any]:
    return {
        "profile_text": scenario.profile_text,
        "roles": scenario.roles,
        "skills": scenario.skills,
        "locations": scenario.locations,
        "experience_level": scenario.experience_level,
        "work_modes": scenario.work_modes,
        "employment_types": "",
        "experience_years": None,
    }
