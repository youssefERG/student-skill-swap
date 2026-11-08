SKILL_GROUPS = {
    "Programming languages": [
        "Python",
        "JavaScript",
        "TypeScript",
        "Java",
        "C",
        "C++",
        "C#",
        "PHP",
        "Ruby",
        "Go",
        "Rust",
        "Bash",
    ],
    "Web development": [
        "HTML",
        "CSS",
        "Flask",
        "Django",
        "React",
        "Node.js",
        "REST APIs",
    ],
    "Data and AI": [
        "SQL",
        "Data analysis",
        "Machine learning",
    ],
    "IT and tools": [
        "Git and GitHub",
        "Linux",
        "Cybersecurity basics",
        "Computer networking",
        "Docker",
        "Cloud computing",
        "UI/UX for software",
    ],
}

ALL_SKILLS = [
    skill
    for skills_in_group in SKILL_GROUPS.values()
    for skill in skills_in_group
]

ALLOWED_SKILLS = set(ALL_SKILLS)