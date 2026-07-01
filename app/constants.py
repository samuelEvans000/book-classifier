"""Shared constants for the classification pipeline."""

MAIN_CATEGORIES = {
    "Psychology", "Neuroscience", "Philosophy", "History", "Sociology",
    "Anthropology", "Economics", "Business", "Politics", "Law", "Education",
    "Mathematics", "Physics", "Chemistry", "Biology", "Medicine", "Health",
    "Computer Science", "Artificial Intelligence", "Data Science", "Cybersecurity",
    "Engineering", "Environmental Science", "Astronomy", "Religion", "Art",
    "Design", "Architecture", "Music", "Language", "Literature", "Self-Help",
    "Personal Development", "Productivity", "Finance", "Investing", "Leadership",
    "Communication", "Marketing", "Entrepreneurship", "Biography", "Memoir",
    "Travel", "Geography",
}

TARGET_AUDIENCES = {"General", "Enthusiast", "Professional", "Academic"}

REQUIRED_SUBCATEGORIES = 10

OUTPUT_FLUSH_EVERY = 100