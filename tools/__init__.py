import shutil
from typing import List
from langchain_core.tools import BaseTool


def is_installed(lib_name: str) -> bool:
    lib = shutil.which(lib_name)
    if lib is None:
        return False
    return True


def get_all_tools() -> List[BaseTool]:
    """
    Get all available tools based on system capabilities and installed dependencies.
    Phase 2A: Enhanced with document intelligence tools.
    """
    tools = []
    
    # Core tools (always available)
    from .file_tools import get_file_tools
    from .research_tools import get_research_tools
    from .reasoning_tools import get_reasoning_tools
    from .math_tools import get_math_tools
    from .multimodal_tools import get_multimodal_tools
    
    tools.extend(get_file_tools())
    tools.extend(get_research_tools())
    tools.extend(get_reasoning_tools())
    tools.extend(get_math_tools())
    tools.extend(get_multimodal_tools())
    
    # Enhanced document intelligence tools (Phase 2A)
    try:
        from .document_intelligence import get_document_intelligence_tools
        tools.extend(get_document_intelligence_tools())
    except ImportError as e:
        print(f"Document intelligence tools not available: {e}")
    
    # Language detection tools (Phase 2B.3)
    try:
        from .language_detection import get_language_detection_tools
        tools.extend(get_language_detection_tools())
    except ImportError as e:
        print(f"Language detection tools not available: {e}")
    
    # Enhanced research tools (Phase 2B.3)
    try:
        from .enhanced_research_tools import get_enhanced_research_tools
        tools.extend(get_enhanced_research_tools())
    except ImportError as e:
        print(f"Enhanced research tools not available: {e}")
    
    # Optional tools based on system capabilities
    try:
        from .plotting import get_plotting_tools
        tools.extend(get_plotting_tools())
    except ImportError:
        pass
    
    try:
        from .agents_tools import get_agent_tools
        tools.extend(get_agent_tools())
    except ImportError:
        pass
    
    return tools




