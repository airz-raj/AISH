#!/usr/bin/env python3
# zomode/project_map.py
"""
Interactive Project Dependency Map for AISH Z-Omode
Analyzes Python projects and creates terminal-based dependency visualizations
"""

import os
import sys
import ast
import json
import time
import threading
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any, Tuple
import re

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = LIGHTRED_EX = LIGHTCYAN_EX = LIGHTBLUE_EX = ''
    class Style:
        RESET_ALL = ''

# Optional dependencies for enhanced functionality
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

# Terminal graphics characters
GRAPH_CHARS = {
    'horizontal': '─',
    'vertical': '│',
    'top_left': '┌',
    'top_right': '┐',
    'bottom_left': '└',
    'bottom_right': '┘',
    'cross': '┼',
    'tee_down': '┬',
    'tee_up': '┴',
    'tee_right': '├',
    'tee_left': '┤',
    'node': '●',
    'connection': '→',
    'branch': '├─',
    'last_branch': '└─'
}

class ProjectAnalyzer:
    """Analyzes Python project structure and dependencies"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.dependencies = defaultdict(set)
        self.reverse_dependencies = defaultdict(set)
        self.file_info = {}
        self.external_imports = defaultdict(set)
        self.project_files = []
        
    def analyze_project(self) -> Dict[str, Any]:
        """Main analysis function"""
        print(f"{Fore.CYAN}🔍 Analyzing project: {self.project_path.name}{Style.RESET_ALL}")
        
        # Find all Python files
        self.find_python_files()
        
        # Analyze each file
        total_files = len(self.project_files)
        for i, file_path in enumerate(self.project_files, 1):
            print(f"\rAnalyzing... {i}/{total_files} files", end='', flush=True)
            self.analyze_file(file_path)
        
        print(f"\r{Fore.GREEN}✅ Analysis complete: {total_files} files processed{Style.RESET_ALL}")
        
        return {
            'dependencies': dict(self.dependencies),
            'reverse_dependencies': dict(self.reverse_dependencies),
            'file_info': self.file_info,
            'external_imports': dict(self.external_imports),
            'project_files': [str(f) for f in self.project_files]
        }
    
    def find_python_files(self):
        """Recursively find all Python files in project"""
        self.project_files = []
        for root, dirs, files in os.walk(self.project_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', 'node_modules']]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('.'):
                    self.project_files.append(Path(root) / file)
    
    def analyze_file(self, file_path: Path):
        """Analyze a single Python file for imports and structure"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Get relative path for internal reference
            rel_path = file_path.relative_to(self.project_path)
            module_name = str(rel_path).replace('/', '.').replace('\\', '.').replace('.py', '')
            
            # Initialize file info
            self.file_info[module_name] = {
                'path': str(rel_path),
                'lines': len(content.splitlines()),
                'classes': [],
                'functions': [],
                'imports': [],
                'complexity': 0
            }
            
            # Analyze imports and structure
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.process_import(module_name, alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.process_import(module_name, node.module, is_from=True)
                
                elif isinstance(node, ast.ClassDef):
                    self.file_info[module_name]['classes'].append(node.name)
                
                elif isinstance(node, ast.FunctionDef):
                    self.file_info[module_name]['functions'].append(node.name)
                    
                elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                    self.file_info[module_name]['complexity'] += 1
                    
        except Exception as e:
            # Handle parsing errors gracefully
            self.file_info[module_name] = {
                'path': str(file_path.relative_to(self.project_path)),
                'error': str(e),
                'lines': 0,
                'classes': [],
                'functions': [],
                'imports': [],
                'complexity': 0
            }
    
    def process_import(self, module_name: str, import_name: str, is_from: bool = False):
        """Process an import statement"""
        self.file_info[module_name]['imports'].append(import_name)
        
        # Check if it's an internal dependency
        if self.is_internal_module(import_name):
            self.dependencies[module_name].add(import_name)
            self.reverse_dependencies[import_name].add(module_name)
        else:
            # External dependency
            self.external_imports[module_name].add(import_name)
    
    def is_internal_module(self, module_name: str) -> bool:
        """Check if module is part of the current project"""
        # Convert import to file path
        potential_paths = [
            self.project_path / f"{module_name}.py",
            self.project_path / module_name / "__init__.py"
        ]
        
        # Also check for relative imports within project structure
        for file_path in self.project_files:
            rel_path = file_path.relative_to(self.project_path)
            file_module = str(rel_path).replace('/', '.').replace('\\', '.').replace('.py', '')
            if module_name == file_module or module_name.startswith(file_module + '.'):
                return True
        
        return any(path.exists() for path in potential_paths)

class TerminalGraphRenderer:
    """Renders dependency graphs in terminal using ASCII/Unicode"""
    
    def __init__(self, analysis_data: Dict[str, Any]):
        self.data = analysis_data
        self.dependencies = analysis_data['dependencies']
        self.file_info = analysis_data['file_info']
        self.external_imports = analysis_data['external_imports']
        
    def render_tree_view(self, start_module: Optional[str] = None):
        """Render as tree structure"""
        print(f"{Fore.CYAN}🌳 Project Dependency Tree{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        if start_module:
            self._render_subtree(start_module, "", set())
        else:
            # Find root modules (no dependencies)
            roots = []
            all_modules = set(self.dependencies.keys())
            all_deps = set()
            for deps in self.dependencies.values():
                all_deps.update(deps)
            
            roots = all_modules - all_deps
            if not roots:
                roots = list(all_modules)[:5]  # Show first 5 if no clear roots
            
            for i, root in enumerate(sorted(roots)):
                is_last = i == len(roots) - 1
                prefix = GRAPH_CHARS['last_branch'] if is_last else GRAPH_CHARS['branch']
                self._render_subtree(root, prefix, set())
    
    def _render_subtree(self, module: str, prefix: str, visited: Set[str]):
        """Recursively render dependency subtree"""
        if module in visited:
            print(f"{prefix}{Fore.YELLOW}{module} (circular){Style.RESET_ALL}")
            return
        
        visited.add(module)
        
        # Get module info
        info = self.file_info.get(module, {})
        lines = info.get('lines', 0)
        complexity = info.get('complexity', 0)
        
        # Color based on complexity
        if complexity > 10:
            color = Fore.RED
        elif complexity > 5:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN
        
        # Display module with metadata
        print(f"{prefix}{color}{module}{Style.RESET_ALL} "
              f"{Fore.LIGHTBLACK_EX}({lines}L, {complexity}C){Style.RESET_ALL}")
        
        # Render dependencies
        deps = sorted(self.dependencies.get(module, set()))
        for i, dep in enumerate(deps):
            is_last_dep = i == len(deps) - 1
            if prefix.endswith(GRAPH_CHARS['last_branch']):
                new_prefix = "    " + (GRAPH_CHARS['last_branch'] if is_last_dep else GRAPH_CHARS['branch'])
            else:
                new_prefix = prefix.replace(GRAPH_CHARS['branch'], "│   ").replace(GRAPH_CHARS['last_branch'], "    ")
                new_prefix += GRAPH_CHARS['last_branch'] if is_last_dep else GRAPH_CHARS['branch']
            
            self._render_subtree(dep, new_prefix, visited.copy())
    
    def render_network_view(self):
        """Render as network graph (requires networkx)"""
        if not HAS_NETWORKX:
            print(f"{Fore.YELLOW}⚠ networkx not available. Install with: pip install networkx{Style.RESET_ALL}")
            self.render_adjacency_matrix()
            return
        
        # Create networkx graph
        G = nx.DiGraph()
        
        # Add nodes and edges
        for module, deps in self.dependencies.items():
            G.add_node(module)
            for dep in deps:
                G.add_edge(module, dep)
        
        # Simple terminal layout
        print(f"{Fore.CYAN}🕸️ Network Dependency Graph{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        # Check for cycles first
        try:
            if not nx.is_directed_acyclic_graph(G):
                print(f"{Fore.YELLOW}⚠ Graph contains cycles - using alternative layout{Style.RESET_ALL}")
                self.render_cycle_aware_network(G)
                return
            
            # If no cycles, use topological sort
            levels = list(nx.topological_generations(G))
            for level_num, level_nodes in enumerate(levels):
                print(f"\n{Fore.MAGENTA}Level {level_num}:{Style.RESET_ALL}")
                for node in sorted(level_nodes):
                    deps = list(self.dependencies.get(node, []))
                    dep_str = f" → {', '.join(deps[:3])}" if deps else ""
                    if len(deps) > 3:
                        dep_str += f" (+{len(deps)-3} more)"
                    
                    info = self.file_info.get(node, {})
                    complexity = info.get('complexity', 0)
                    color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
                    
                    print(f"  {color}●{Style.RESET_ALL} {node}{dep_str}")
        
        except nx.NetworkXError as e:
            print(f"{Fore.YELLOW}⚠ NetworkX error: {e}{Style.RESET_ALL}")
            # Fallback to simple adjacency matrix
            self.render_adjacency_matrix()
        except Exception as e:
            print(f"{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            self.render_adjacency_matrix()
    
    def render_cycle_aware_network(self, G):
        """Render network view that handles cycles gracefully"""
        print(f"{Fore.YELLOW}🔄 Cycle-aware network layout:{Style.RESET_ALL}")
        
        # Find strongly connected components (groups of mutually dependent modules)
        try:
            sccs = list(nx.strongly_connected_components(G))
            
            # Group by SCC size
            single_nodes = []
            small_cycles = []
            large_cycles = []
            
            for scc in sccs:
                if len(scc) == 1:
                    single_nodes.extend(scc)
                elif len(scc) <= 3:
                    small_cycles.append(scc)
                else:
                    large_cycles.append(scc)
            
            # Display single nodes first
            if single_nodes:
                print(f"\n{Fore.GREEN}📄 Independent modules:{Style.RESET_ALL}")
                for node in sorted(single_nodes):
                    deps = list(self.dependencies.get(node, []))
                    dep_count = len(deps)
                    complexity = self.file_info.get(node, {}).get('complexity', 0)
                    color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
                    print(f"  {color}●{Style.RESET_ALL} {node} ({dep_count} deps)")
            
            # Display small cycles
            if small_cycles:
                print(f"\n{Fore.YELLOW}🔄 Small dependency cycles:{Style.RESET_ALL}")
                for i, cycle in enumerate(small_cycles, 1):
                    cycle_list = sorted(list(cycle))
                    print(f"  {i}. {' ↔ '.join(cycle_list)}")
            
            # Display large cycles
            if large_cycles:
                print(f"\n{Fore.RED}🌀 Large dependency cycles:{Style.RESET_ALL}")
                for i, cycle in enumerate(large_cycles, 1):
                    cycle_list = sorted(list(cycle))
                    print(f"  {i}. Complex cycle with {len(cycle_list)} modules:")
                    for module in cycle_list:
                        print(f"     • {module}")
                        
        except Exception as e:
            print(f"{Fore.RED}❌ Error analyzing cycles: {e}{Style.RESET_ALL}")
            # Final fallback
            self.render_simple_list_view()
    
    def render_simple_list_view(self):
        """Simple fallback view when other methods fail"""
        print(f"{Fore.CYAN}📋 Simple Module List View{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        modules = sorted(self.dependencies.keys())
        for module in modules:
            deps = self.dependencies.get(module, set())
            dep_count = len(deps)
            complexity = self.file_info.get(module, {}).get('complexity', 0)
            
            color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
            print(f"{color}●{Style.RESET_ALL} {module} ({dep_count} deps, {complexity}C)")
            
            if deps and dep_count <= 3:
                for dep in sorted(deps):
                    print(f"    → {dep}")
            elif deps:
                dep_list = sorted(list(deps))
                print(f"    → {', '.join(dep_list[:2])} (+{dep_count-2} more)")
    
    def render_adjacency_matrix(self):
        """Fallback: render as adjacency matrix"""
        modules = sorted(set(self.dependencies.keys()) | 
                        set().union(*self.dependencies.values()))
        
        if len(modules) > 20:
            print(f"{Fore.YELLOW}Project too large for matrix view. Showing summary instead.{Style.RESET_ALL}")
            self.render_summary()
            return
        
        print(f"{Fore.CYAN}📊 Dependency Matrix{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        # Header
        print("    ", end="")
        for i, mod in enumerate(modules):
            print(f"{i:2}", end=" ")
        print()
        
        # Matrix
        for i, mod1 in enumerate(modules):
            print(f"{i:2}: ", end="")
            for j, mod2 in enumerate(modules):
                if mod2 in self.dependencies.get(mod1, set()):
                    print(f"{Fore.GREEN}●{Style.RESET_ALL} ", end=" ")
                else:
                    print("  ", end=" ")
            print(f" {mod1}")
    
    def render_summary(self):
        """Render project summary with key metrics"""
        print(f"{Fore.CYAN}📋 Project Dependency Summary{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        total_modules = len(self.file_info)
        total_lines = sum(info.get('lines', 0) for info in self.file_info.values())
        total_complexity = sum(info.get('complexity', 0) for info in self.file_info.values())
        
        print(f"Total modules: {total_modules}")
        print(f"Total lines: {total_lines:,}")
        print(f"Average complexity: {total_complexity/total_modules:.1f}" if total_modules > 0 else "Average complexity: 0")
        
        # Most complex modules
        print(f"\n{Fore.YELLOW}🔥 Most Complex Modules:{Style.RESET_ALL}")
        complex_modules = sorted(
            [(name, info.get('complexity', 0)) for name, info in self.file_info.items()],
            key=lambda x: x[1], reverse=True
        )[:5]
        
        for name, complexity in complex_modules:
            color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
            print(f"  {color}●{Style.RESET_ALL} {name} ({complexity} complexity points)")
        
        # Most connected modules
        print(f"\n{Fore.YELLOW}🕸️ Most Connected Modules:{Style.RESET_ALL}")
        connected_modules = sorted(
            [(name, len(deps)) for name, deps in self.dependencies.items()],
            key=lambda x: x[1], reverse=True
        )[:5]
        
        for name, dep_count in connected_modules:
            color = Fore.RED if dep_count > 5 else Fore.YELLOW if dep_count > 2 else Fore.GREEN
            print(f"  {color}●{Style.RESET_ALL} {name} ({dep_count} dependencies)")
        
        # External dependencies
        print(f"\n{Fore.YELLOW}📦 External Dependencies:{Style.RESET_ALL}")
        all_external = set()
        for ext_deps in self.external_imports.values():
            all_external.update(ext_deps)
        
        for ext_dep in sorted(all_external)[:10]:
            print(f"  {Fore.LIGHTBLUE_EX}📦{Style.RESET_ALL} {ext_dep}")
        
        if len(all_external) > 10:
            print(f"  {Fore.LIGHTBLACK_EX}... and {len(all_external)-10} more{Style.RESET_ALL}")

class InteractiveExplorer:
    """Interactive exploration of dependency graph"""
    
    def __init__(self, analyzer: ProjectAnalyzer):
        self.analyzer = analyzer
        self.current_module = None
        self.view_history = deque(maxlen=10)
        
    def start_interactive_mode(self):
        """Start interactive exploration"""
        print(f"{Fore.CYAN}🎮 Interactive Project Explorer{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Commands: view <module>, deps <module>, back, help, exit{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        # Show available modules
        modules = sorted(self.analyzer.file_info.keys())
        print(f"\n{Fore.MAGENTA}📁 Available Modules:{Style.RESET_ALL}")
        for i, module in enumerate(modules[:10], 1):
            info = self.analyzer.file_info[module]
            lines = info.get('lines', 0)
            complexity = info.get('complexity', 0)
            print(f"  {i:2}. {module} ({lines}L, {complexity}C)")
        
        if len(modules) > 10:
            print(f"     {Fore.LIGHTBLACK_EX}... and {len(modules)-10} more (use 'list' to see all){Style.RESET_ALL}")
        
        while True:
            try:
                command = input(f"\n{Fore.GREEN}explorer> {Style.RESET_ALL}").strip()
                if not command:
                    continue
                
                if command.lower() in ['exit', 'quit', 'q']:
                    break
                
                self.process_command(command)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Use 'exit' to quit explorer{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    
    def process_command(self, command: str):
        """Process interactive command"""
        parts = command.lower().split()
        cmd = parts[0] if parts else ""
        
        if cmd == "help":
            self.show_help()
        elif cmd == "list":
            self.list_modules()
        elif cmd == "view" and len(parts) > 1:
            self.view_module(' '.join(parts[1:]))
        elif cmd == "deps" and len(parts) > 1:
            self.show_dependencies(' '.join(parts[1:]))
        elif cmd == "reverse" and len(parts) > 1:
            self.show_reverse_dependencies(' '.join(parts[1:]))
        elif cmd == "back":
            self.go_back()
        elif cmd == "external":
            self.show_external_deps()
        elif cmd == "summary":
            renderer = TerminalGraphRenderer(self.analyzer.analyze_project())
            renderer.render_summary()
        elif cmd.isdigit():
            # Quick access by number
            self.view_module_by_number(int(cmd))
        else:
            print(f"{Fore.RED}Unknown command: {command}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Type 'help' for available commands{Style.RESET_ALL}")
    
    def show_help(self):
        """Show interactive help"""
        print(f"\n{Fore.CYAN}🎮 Interactive Explorer Commands:{Style.RESET_ALL}")
        commands = [
            ("view <module>", "Show detailed info about a module"),
            ("deps <module>", "Show what a module depends on"),
            ("reverse <module>", "Show what depends on a module"),
            ("list", "List all modules"),
            ("external", "Show external dependencies"),
            ("summary", "Show project summary"),
            ("<number>", "Quick view module by number"),
            ("back", "Go back in history"),
            ("help", "Show this help"),
            ("exit", "Exit explorer")
        ]
        
        for cmd, desc in commands:
            print(f"  {Fore.YELLOW}{cmd:<15}{Style.RESET_ALL} - {desc}")
    
    def list_modules(self):
        """List all modules with details"""
        modules = sorted(self.analyzer.file_info.keys())
        print(f"\n{Fore.MAGENTA}📁 All Project Modules ({len(modules)} total):{Style.RESET_ALL}")
        
        for i, module in enumerate(modules, 1):
            info = self.analyzer.file_info[module]
            lines = info.get('lines', 0)
            complexity = info.get('complexity', 0)
            dep_count = len(self.analyzer.dependencies.get(module, set()))
            
            # Color based on complexity
            color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
            
            print(f"  {i:2}. {color}{module}{Style.RESET_ALL} "
                  f"{Fore.LIGHTBLACK_EX}({lines}L, {complexity}C, {dep_count}D){Style.RESET_ALL}")
    
    def view_module(self, module_name: str):
        """Show detailed module information"""
        # Find best match
        module = self.find_module(module_name)
        if not module:
            return
        
        self.view_history.append(module)
        self.current_module = module
        
        info = self.analyzer.file_info[module]
        
        print(f"\n{Fore.CYAN}📄 Module: {module}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        print(f"Path: {info.get('path', 'Unknown')}")
        print(f"Lines: {info.get('lines', 0)}")
        print(f"Complexity: {info.get('complexity', 0)}")
        print(f"Classes: {len(info.get('classes', []))}")
        print(f"Functions: {len(info.get('functions', []))}")
        
        # Show classes and functions
        if info.get('classes'):
            print(f"\n{Fore.YELLOW}🏛️ Classes:{Style.RESET_ALL}")
            for cls in info['classes'][:5]:
                print(f"  • {cls}")
            if len(info['classes']) > 5:
                print(f"  {Fore.LIGHTBLACK_EX}... and {len(info['classes'])-5} more{Style.RESET_ALL}")
        
        if info.get('functions'):
            print(f"\n{Fore.YELLOW}⚙️ Functions:{Style.RESET_ALL}")
            for func in info['functions'][:5]:
                print(f"  • {func}")
            if len(info['functions']) > 5:
                print(f"  {Fore.LIGHTBLACK_EX}... and {len(info['functions'])-5} more{Style.RESET_ALL}")
        
        # Show dependencies
        deps = self.analyzer.dependencies.get(module, set())
        if deps:
            print(f"\n{Fore.YELLOW}📥 Dependencies ({len(deps)}):{Style.RESET_ALL}")
            for dep in sorted(deps):
                print(f"  {Fore.GREEN}→{Style.RESET_ALL} {dep}")
        
        # Show reverse dependencies
        reverse_deps = self.analyzer.reverse_dependencies.get(module, set())
        if reverse_deps:
            print(f"\n{Fore.YELLOW}📤 Used by ({len(reverse_deps)}):{Style.RESET_ALL}")
            for rdep in sorted(reverse_deps):
                print(f"  {Fore.BLUE}←{Style.RESET_ALL} {rdep}")
        
        # Show external imports
        external = self.analyzer.external_imports.get(module, set())
        if external:
            print(f"\n{Fore.YELLOW}📦 External Imports ({len(external)}):{Style.RESET_ALL}")
            for ext in sorted(external)[:5]:
                print(f"  {Fore.LIGHTBLUE_EX}📦{Style.RESET_ALL} {ext}")
            if len(external) > 5:
                print(f"  {Fore.LIGHTBLACK_EX}... and {len(external)-5} more{Style.RESET_ALL}")
    
    def show_dependencies(self, module_name: str):
        """Show what a module depends on"""
        module = self.find_module(module_name)
        if not module:
            return
        
        deps = self.analyzer.dependencies.get(module, set())
        print(f"\n{Fore.CYAN}📥 {module} depends on:{Style.RESET_ALL}")
        
        if not deps:
            print(f"  {Fore.YELLOW}No internal dependencies{Style.RESET_ALL}")
            return
        
        for dep in sorted(deps):
            info = self.analyzer.file_info.get(dep, {})
            complexity = info.get('complexity', 0)
            color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
            print(f"  {color}→{Style.RESET_ALL} {dep} ({complexity}C)")
    
    def show_reverse_dependencies(self, module_name: str):
        """Show what depends on a module"""
        module = self.find_module(module_name)
        if not module:
            return
        
        reverse_deps = self.analyzer.reverse_dependencies.get(module, set())
        print(f"\n{Fore.CYAN}📤 Modules that depend on {module}:{Style.RESET_ALL}")
        
        if not reverse_deps:
            print(f"  {Fore.YELLOW}No modules depend on this{Style.RESET_ALL}")
            return
        
        for rdep in sorted(reverse_deps):
            info = self.analyzer.file_info.get(rdep, {})
            complexity = info.get('complexity', 0)
            color = Fore.RED if complexity > 10 else Fore.YELLOW if complexity > 5 else Fore.GREEN
            print(f"  {color}←{Style.RESET_ALL} {rdep} ({complexity}C)")
    
    def show_external_deps(self):
        """Show all external dependencies"""
        all_external = set()
        usage_count = defaultdict(int)
        
        for module, ext_deps in self.analyzer.external_imports.items():
            for ext_dep in ext_deps:
                all_external.add(ext_dep)
                usage_count[ext_dep] += 1
        
        print(f"\n{Fore.CYAN}📦 External Dependencies ({len(all_external)} total):{Style.RESET_ALL}")
        
        # Sort by usage frequency
        sorted_external = sorted(usage_count.items(), key=lambda x: x[1], reverse=True)
        
        for ext_dep, count in sorted_external:
            color = Fore.RED if count > 5 else Fore.YELLOW if count > 2 else Fore.GREEN
            print(f"  {color}📦{Style.RESET_ALL} {ext_dep} {Fore.LIGHTBLACK_EX}(used in {count} modules){Style.RESET_ALL}")
    
    def view_module_by_number(self, number: int):
        """View module by list number"""
        modules = sorted(self.analyzer.file_info.keys())
        if 1 <= number <= len(modules):
            self.view_module(modules[number - 1])
        else:
            print(f"{Fore.RED}Invalid module number. Use 'list' to see all modules.{Style.RESET_ALL}")
    
    def find_module(self, module_name: str) -> Optional[str]:
        """Find module with fuzzy matching"""
        # Exact match
        if module_name in self.analyzer.file_info:
            return module_name
        
        # Partial match
        matches = [m for m in self.analyzer.file_info.keys() if module_name.lower() in m.lower()]
        
        if not matches:
            print(f"{Fore.RED}Module '{module_name}' not found{Style.RESET_ALL}")
            return None
        
        if len(matches) == 1:
            return matches[0]
        
        # Multiple matches - let user choose
        print(f"{Fore.YELLOW}Multiple matches for '{module_name}':{Style.RESET_ALL}")
        for i, match in enumerate(matches[:5], 1):
            print(f"  {i}. {match}")
        
        try:
            choice = input(f"{Fore.CYAN}Select module (1-{min(5, len(matches))}): {Style.RESET_ALL}")
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                return matches[idx]
        except ValueError:
            pass
        
        print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
        return None
    
    def go_back(self):
        """Go back to previous module"""
        if len(self.view_history) > 1:
            self.view_history.pop()  # Remove current
            previous = self.view_history[-1]
            self.view_module(previous)
        else:
            print(f"{Fore.YELLOW}No previous module in history{Style.RESET_ALL}")

# -------------------------
# Main Project Map Commands
# -------------------------

def project_map_analyze(args: List[str] = None):
    """Analyze project dependencies"""
    project_path = args[0] if args else "."
    
    if not os.path.exists(project_path):
        print(f"{Fore.RED}❌ Path not found: {project_path}{Style.RESET_ALL}")
        return
    
    try:
        analyzer = ProjectAnalyzer(project_path)
        analysis_data = analyzer.analyze_project()
        
        # Store for interactive use
        global current_analyzer
        current_analyzer = analyzer
        
        print(f"{Fore.GREEN}✅ Project '{analyzer.project_path.name}' analyzed successfully{Style.RESET_ALL}")
        return analysis_data
        
    except Exception as e:
        print(f"{Fore.RED}❌ Analysis failed: {e}{Style.RESET_ALL}")
        return None

def project_map_tree(args: List[str] = None):
    """Show project as dependency tree"""
    global current_analyzer
    if current_analyzer is None:
        print(f"{Fore.YELLOW}❌ No project analyzed yet. Run 'Analyze Project' first{Style.RESET_ALL}")
        return
    
    try:
        renderer = TerminalGraphRenderer(current_analyzer.analyze_project())
        start_module = args[0] if args else None
        renderer.render_tree_view(start_module)
    except Exception as e:
        print(f"{Fore.RED}❌ Error generating tree view: {e}{Style.RESET_ALL}")

def project_map_network(args: List[str] = None):
    """Show project as network graph"""
    global current_analyzer
    if current_analyzer is None:
        print(f"{Fore.YELLOW}❌ No project analyzed yet. Run 'Analyze Project' first{Style.RESET_ALL}")
        return
    
    try:
        renderer = TerminalGraphRenderer(current_analyzer.analyze_project())
        renderer.render_network_view()
    except Exception as e:
        print(f"{Fore.RED}❌ Error generating network view: {e}{Style.RESET_ALL}")

def project_map_summary(args: List[str] = None):
    """Show project summary with key metrics"""
    global current_analyzer
    if current_analyzer is None:
        print(f"{Fore.YELLOW}❌ No project analyzed yet. Run 'Analyze Project' first{Style.RESET_ALL}")
        return
    
    try:
        renderer = TerminalGraphRenderer(current_analyzer.analyze_project())
        renderer.render_summary()
    except Exception as e:
        print(f"{Fore.RED}❌ Error generating summary: {e}{Style.RESET_ALL}")

def project_map_interactive(args: List[str] = None):
    """Start interactive project exploration"""
    global current_analyzer
    if current_analyzer is None:
        print(f"{Fore.YELLOW}❌ No project analyzed yet. Run 'Analyze Project' first{Style.RESET_ALL}")
        return
    
    try:
        explorer = InteractiveExplorer(current_analyzer)
        explorer.start_interactive_mode()
    except Exception as e:
        print(f"{Fore.RED}❌ Error starting interactive mode: {e}{Style.RESET_ALL}")

def project_map_export(args: List[str] = None):
    """Export project analysis to file"""
    if 'current_analyzer' not in globals():
        print(f"{Fore.YELLOW}Run 'project analyze' first{Style.RESET_ALL}")
        return
    
    output_file = args[0] if args else "project_analysis.json"
    
    try:
        analysis_data = current_analyzer.analyze_project()
        
        # Convert sets to lists for JSON serialization
        json_data = {}
        for key, value in analysis_data.items():
            if isinstance(value, dict):
                json_data[key] = {k: list(v) if isinstance(v, set) else v for k, v in value.items()}
            else:
                json_data[key] = value
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"{Fore.GREEN}✅ Analysis exported to: {output_file}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Export failed: {e}{Style.RESET_ALL}")

def project_map_find_cycles(args: List[str] = None):
    """Find circular dependencies in project"""
    if 'current_analyzer' not in globals():
        print(f"{Fore.YELLOW}Run 'project analyze' first{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}🔄 Checking for circular dependencies...{Style.RESET_ALL}")
    
    # Simple cycle detection using DFS
    visited = set()
    rec_stack = set()
    cycles = []
    
    def dfs(module, path):
        if module in rec_stack:
            # Found cycle
            cycle_start = path.index(module)
            cycle = path[cycle_start:] + [module]
            cycles.append(cycle)
            return
        
        if module in visited:
            return
        
        visited.add(module)
        rec_stack.add(module)
        
        for dep in current_analyzer.dependencies.get(module, set()):
            dfs(dep, path + [module])
        
        rec_stack.remove(module)
    
    # Check all modules
    for module in current_analyzer.file_info.keys():
        if module not in visited:
            dfs(module, [])
    
    if cycles:
        print(f"{Fore.RED}❌ Found {len(cycles)} circular dependencies:{Style.RESET_ALL}")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " → ".join(cycle)
            print(f"  {i}. {cycle_str}")
    else:
        print(f"{Fore.GREEN}✅ No circular dependencies found{Style.RESET_ALL}")

def project_map_stats(args: List[str] = None):
    """Show detailed project statistics"""
    if 'current_analyzer' not in globals():
        print(f"{Fore.YELLOW}Run 'project analyze' first{Style.RESET_ALL}")
        return
    
    analysis = current_analyzer.analyze_project()
    
    print(f"{Fore.CYAN}📊 Project Statistics{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    # Basic stats
    total_modules = len(analysis['file_info'])
    total_lines = sum(info.get('lines', 0) for info in analysis['file_info'].values())
    total_complexity = sum(info.get('complexity', 0) for info in analysis['file_info'].values())
    total_deps = sum(len(deps) for deps in analysis['dependencies'].values())
    
    print(f"📁 Total modules: {total_modules}")
    print(f"📄 Total lines: {total_lines:,}")
    print(f"🔥 Total complexity: {total_complexity}")
    print(f"🔗 Total dependencies: {total_deps}")
    print(f"📊 Avg complexity per module: {total_complexity/total_modules:.1f}" if total_modules > 0 else "📊 Avg complexity per module: 0")
    
    # Complexity distribution
    complexity_ranges = {'Low (0-5)': 0, 'Medium (6-10)': 0, 'High (11+)': 0}
    for info in analysis['file_info'].values():
        complexity = info.get('complexity', 0)
        if complexity <= 5:
            complexity_ranges['Low (0-5)'] += 1
        elif complexity <= 10:
            complexity_ranges['Medium (6-10)'] += 1
        else:
            complexity_ranges['High (11+)'] += 1
    
    print(f"\n{Fore.YELLOW}🎯 Complexity Distribution:{Style.RESET_ALL}")
    for range_name, count in complexity_ranges.items():
        percentage = (count / total_modules * 100) if total_modules > 0 else 0
        print(f"  {range_name}: {count} ({percentage:.1f}%)")
    
    # External dependency stats
    all_external = set()
    for ext_deps in analysis['external_imports'].values():
        all_external.update(ext_deps)
    
    print(f"\n{Fore.YELLOW}📦 External Dependencies:{Style.RESET_ALL}")
    print(f"  Unique packages: {len(all_external)}")
    
    # Most used external packages
    ext_usage = defaultdict(int)
    for ext_deps in analysis['external_imports'].values():
        for ext_dep in ext_deps:
            ext_usage[ext_dep] += 1
    
    if ext_usage:
        print(f"  Most used: {max(ext_usage.items(), key=lambda x: x[1])}")

# -------------------------
# Menu Functions
# -------------------------

def typewriter(text, delay=0.01, color=Fore.LIGHTWHITE_EX):
    for ch in text:
        sys.stdout.write(f"{color}{ch}")
        sys.stdout.flush()
        time.sleep(delay)
    print()

def print_colored_menu(options):
    for idx, opt in enumerate(options, 1):
        print(f"{Fore.LIGHTRED_EX}{idx}) {Fore.LIGHTWHITE_EX}{opt}")
    print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back")

def loading_dots(message="Loading", duration=1.0):
    dots = ["   ", ".  ", ".. ", "..."]
    end_time = time.time() + duration
    idx = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{Fore.LIGHTGREEN_EX}{message}{dots[idx % len(dots)]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.3)
        idx += 1
    print("\r" + " "*50 + "\r", end="")

def project_dependency_menu():
    """Main menu for project dependency mapping"""
    typewriter("Initializing Interactive Project Dependency Map...", color=Fore.LIGHTCYAN_EX)
    loading_dots("Loading project analyzer", duration=1.5)
    
    # Initialize global analyzer variable safely
    global current_analyzer
    if current_analyzer is None:
        current_analyzer = None
    
    while True:
        typewriter("\n=== 🗺️ Interactive Project Dependency Map ===", color=Fore.LIGHTRED_EX)
        
        # Show current project safely
        try:
            if current_analyzer and hasattr(current_analyzer, 'project_path'):
                project_name = current_analyzer.project_path.name
                print(f"Current project: {Fore.GREEN}{project_name}{Style.RESET_ALL}")
            else:
                print(f"Current project: {Fore.YELLOW}None - analyze a project first{Style.RESET_ALL}")
        except Exception:
            print(f"Current project: {Fore.YELLOW}None - analyze a project first{Style.RESET_ALL}")
        
        options = [
            "Analyze Project (select folder)",
            "Tree View (hierarchical)",
            "Network View (graph layout)", 
            "Project Summary & Stats",
            "Interactive Explorer",
            "Find Circular Dependencies",
            "Export Analysis",
            "Quick Analyze Current Directory"
        ]
        print_colored_menu(options)
        
        choice = input(Fore.LIGHTCYAN_EX + "Select an option: " + Style.RESET_ALL).strip()
        
        if choice == "0":
            break
            
        elif choice == "1":
            project_path = input(f"{Fore.CYAN}Enter project path (or '.' for current): {Style.RESET_ALL}").strip()
            if not project_path:
                project_path = "."
            loading_dots("Analyzing project", 2.0)
            project_map_analyze([project_path])
            
        elif choice == "2":
            module_filter = input(f"{Fore.CYAN}Start from module (or empty for roots): {Style.RESET_ALL}").strip()
            args = [module_filter] if module_filter else []
            project_map_tree(args)
            
        elif choice == "3":
            loading_dots("Generating network view", 1.0)
            project_map_network()
            
        elif choice == "4":
            loading_dots("Calculating statistics", 1.0)
            project_map_stats()
            
        elif choice == "5":
            project_map_interactive()
            
        elif choice == "6":
            loading_dots("Searching for cycles", 1.5)
            project_map_find_cycles()
            
        elif choice == "7":
            output_file = input(f"{Fore.CYAN}Output filename (default: project_analysis.json): {Style.RESET_ALL}").strip()
            args = [output_file] if output_file else []
            project_map_export(args)
            
        elif choice == "8":
            loading_dots("Quick analyzing current directory", 1.5)
            project_map_analyze(["."])
            
        else:
            typewriter("❌ Invalid option", color=Fore.LIGHTRED_EX)

# -------------------------
# Command Registry for Integration
# -------------------------
PROJECT_MAP_COMMANDS = {
    "project_analyze": project_map_analyze,
    "project_tree": project_map_tree,
    "project_network": project_map_network,
    "project_summary": project_map_summary,
    "project_interactive": project_map_interactive,
    "project_stats": project_map_stats,
    "project_cycles": project_map_find_cycles,
    "project_export": project_map_export
}

# Global analyzer instance
current_analyzer = None

# Main entry point for the menu
if __name__ == "__main__":
    project_dependency_menu()