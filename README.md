[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Shared-Goals/SOSenki)

# Implementation Roadmap

Week 1-2: Foundation
✅ Run dead code analysis
✅ Remove identified dead files
✅ Set up coverage reporting
✅ Document all findings

Week 2-3: Localization
✅ Implement backend localization
✅ Add translation files
✅ Integrate with bot handlers
✅ Add language detection

Week 3-4: Testing
✅ Add seeding unit tests
✅ Add feature tests
✅ Achieve 80%+ coverage
✅ Add test documentation

Week 4-5: Design
✅ Install Figma MCP
✅ Generate design tokens
✅ Update CSS architecture
✅ Implement component system

Week 5-6: Refactoring
✅ Extract base services
✅ Consolidate duplicated code
✅ Improve error handling
✅ Update documentation

## Best Practices Checklist

Code Quality:

- Use ruff for consistent formatting
- Add type hints everywhere
- Document all public APIs
- Keep functions under 20 lines

Testing:

- Write tests first (TDD)
- Mock external dependencies
- Test edge cases
- Maintain 80%+ coverage

Localization:

- Use key-based translations
- Support RTL languages later
- Test with real users
- Keep translations in sync

Design System:

- Use CSS variables
- Follow 8px grid system
- Ensure accessibility (WCAG 2.1)
- Test on multiple devices

## Figma Integration Setup

```json
{
  "figma": {
    "fileId": "YOUR_FIGMA_FILE_ID",
    "accessToken": "${FIGMA_ACCESS_TOKEN}",
    "components": {
      "mapping": {
        "Button": "src/static/mini_app/components/button.css",
        "Card": "src/static/mini_app/components/card.css",
        "Header": "src/static/mini_app/components/header.css"
      }
    },
    "colors": {
      "output": "src/static/mini_app/design-tokens.css"
    }
  }
}
```

### Design System Implementation

```css
/* Auto-generated from Figma - DO NOT EDIT MANUALLY */

:root {
  /* Telegram Design System Colors */
  --tg-theme-bg-color: var(--tg-theme-bg-color, #ffffff);
  --tg-theme-text-color: var(--tg-theme-text-color, #000000);
  --tg-theme-hint-color: var(--tg-theme-hint-color, #999999);
  --tg-theme-link-color: var(--tg-theme-link-color, #2481cc);
  --tg-theme-button-color: var(--tg-theme-button-color, #2481cc);
  --tg-theme-button-text-color: var(--tg-theme-button-text-color, #ffffff);
  
  /* Custom Theme Extensions */
  --nature-green: #4a7c59;
  --nature-brown: #8b4513;
  --nature-blue: #4682b4;
  
  /* Spacing Scale (8px base) */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  
  /* Typography Scale */
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-base: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

## Service Layer Refactoring

```python
"""Base service class with common patterns."""

from typing import TypeVar, Generic, Optional, List
from sqlalchemy.orm import Session
from src.models import Base

T = TypeVar('T', bound=Base)

class BaseService(Generic[T]):
    """Base service with CRUD operations."""
    
    def __init__(self, model: type[T], session: Session):
        self.model = model
        self.session = session
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID."""
        return self.session.query(self.model).filter(
            self.model.id == id
        ).first()
    
    def get_all(self, **filters) -> List[T]:
        """Get all entities with optional filters."""
        query = self.session.query(self.model)
        for key, value in filters.items():
            query = query.filter(getattr(self.model, key) == value)
        return query.all()
    
    def create(self, **data) -> T:
        """Create new entity."""
        entity = self.model(**data)
        self.session.add(entity)
        self.session.commit()
        return entity
    
    def update(self, id: int, **data) -> Optional[T]:
        """Update entity."""
        entity = self.get_by_id(id)
        if entity:
            for key, value in data.items():
                setattr(entity, key, value)
            self.session.commit()
        return entity
```
