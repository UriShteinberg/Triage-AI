"""
Generate Architecture Diagram for Clinical Triage Agent
Reflects actual 5-step workflow implementation
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

def create_architecture_diagram():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(7, 9.5, 'Clinical Triage Agent Architecture', 
            fontsize=24, fontweight='bold', ha='center', color='#4a5568')
    
    # Colors
    module_color = '#e3f2fd'
    module_edge = '#1976d2'
    external_color = '#fff3e0'
    external_edge = '#f57c00'
    
    # Step 1: Input Validator
    step1 = FancyBboxPatch((0.5, 7), 2.5, 1.2, boxstyle="round,pad=0.1",
                           edgecolor=module_edge, facecolor=module_color, linewidth=2)
    ax.add_patch(step1)
    ax.text(1.75, 7.75, 'Input Validator', fontsize=12, fontweight='bold', ha='center')
    ax.text(1.75, 7.35, 'Normalization', fontsize=9, ha='center', style='italic', color='#666')
    
    # Step 2: Clinical Rule Engine
    step2 = FancyBboxPatch((0.5, 5), 2.5, 1.2, boxstyle="round,pad=0.1",
                           edgecolor=module_edge, facecolor=module_color, linewidth=2)
    ax.add_patch(step2)
    ax.text(1.75, 5.75, 'Clinical Rule Engine', fontsize=12, fontweight='bold', ha='center')
    ax.text(1.75, 5.35, 'Baseline Urgency', fontsize=9, ha='center', style='italic', color='#666')
    
    # Step 3: Knowledge Retriever
    step3 = FancyBboxPatch((4, 5), 2.5, 1.2, boxstyle="round,pad=0.1",
                           edgecolor=module_edge, facecolor=module_color, linewidth=2)
    ax.add_patch(step3)
    ax.text(5.25, 5.75, 'Knowledge Retriever', fontsize=12, fontweight='bold', ha='center')
    ax.text(5.25, 5.35, 'RAG + Pinecone', fontsize=9, ha='center', style='italic', color='#666')
    
    # Step 4: Decision Engine
    step4 = FancyBboxPatch((7.5, 5), 2.5, 1.2, boxstyle="round,pad=0.1",
                           edgecolor=module_edge, facecolor=module_color, linewidth=2)
    ax.add_patch(step4)
    ax.text(8.75, 5.75, 'Decision Engine', fontsize=12, fontweight='bold', ha='center')
    ax.text(8.75, 5.35, 'LLM Decision Fusion', fontsize=9, ha='center', style='italic', color='#666')
    
    # Step 5: Triage Orchestrator
    step5 = FancyBboxPatch((4, 2.5), 2.5, 1.2, boxstyle="round,pad=0.1",
                           edgecolor=module_edge, facecolor=module_color, linewidth=2)
    ax.add_patch(step5)
    ax.text(5.25, 3.25, 'Triage Orchestrator', fontsize=12, fontweight='bold', ha='center')
    ax.text(5.25, 2.85, 'Output Formatting', fontsize=9, ha='center', style='italic', color='#666')
    
    # External Services
    # Pinecone DB
    pinecone = FancyBboxPatch((11, 5.5), 2.2, 0.8, boxstyle="round,pad=0.1",
                             edgecolor=external_edge, facecolor=external_color, linewidth=2)
    ax.add_patch(pinecone)
    ax.text(12.1, 5.9, 'Pinecone DB', fontsize=11, fontweight='bold', ha='center', color='#f57c00')
    
    # LLMod.ai API
    llm = FancyBboxPatch((11, 4), 2.2, 0.8, boxstyle="round,pad=0.1",
                        edgecolor=external_edge, facecolor=external_color, linewidth=2)
    ax.add_patch(llm)
    ax.text(12.1, 4.4, 'LLMod.ai API', fontsize=11, fontweight='bold', ha='center', color='#f57c00')
    
    # Arrows - Main flow
    # Step 1 to Step 2
    arrow1 = FancyArrowPatch((1.75, 7), (1.75, 6.2), 
                            arrowstyle='->', mutation_scale=20, linewidth=2.5, color='#1976d2')
    ax.add_patch(arrow1)
    
    # Step 2 to Step 3
    arrow2 = FancyArrowPatch((3, 5.6), (4, 5.6), 
                            arrowstyle='->', mutation_scale=20, linewidth=2.5, color='#1976d2')
    ax.add_patch(arrow2)
    
    # Step 3 to Step 4
    arrow3 = FancyArrowPatch((6.5, 5.6), (7.5, 5.6), 
                            arrowstyle='->', mutation_scale=20, linewidth=2.5, color='#1976d2')
    ax.add_patch(arrow3)
    
    # Step 4 to Step 5
    arrow4 = FancyArrowPatch((8.75, 5), (5.25, 3.7), 
                            arrowstyle='->', mutation_scale=20, linewidth=2.5, color='#1976d2')
    ax.add_patch(arrow4)
    
    # Step 2 also feeds into Step 5 (baseline urgency)
    arrow5 = FancyArrowPatch((1.75, 5), (4.5, 3.7), 
                            arrowstyle='->', mutation_scale=20, linewidth=2, color='#1976d2', linestyle='dashed', alpha=0.6)
    ax.add_patch(arrow5)
    
    # External connections
    # Knowledge Retriever to Pinecone
    arrow_pinecone = FancyArrowPatch((6.5, 5.9), (11, 5.9), 
                                    arrowstyle='<->', mutation_scale=15, linewidth=1.5, 
                                    color='#f57c00', linestyle='dotted')
    ax.add_patch(arrow_pinecone)
    
    # Decision Engine to LLMod.ai
    arrow_llm = FancyArrowPatch((10, 5.4), (11, 4.4), 
                               arrowstyle='<->', mutation_scale=15, linewidth=1.5, 
                               color='#f57c00', linestyle='dotted')
    ax.add_patch(arrow_llm)
    
    # Input/Output labels
    ax.text(1.75, 8.5, 'Patient Data', fontsize=10, ha='center', 
            bbox=dict(boxstyle='round', facecolor='#f0f0f0', edgecolor='#999'))
    ax.text(5.25, 1.8, 'KTAS Level + Actions + Justification', fontsize=10, ha='center',
            bbox=dict(boxstyle='round', facecolor='#f0f0f0', edgecolor='#999'))
    
    # Step labels
    ax.text(0.2, 7.6, 'STEP 1', fontsize=9, fontweight='bold', color='#1976d2')
    ax.text(0.2, 5.6, 'STEP 2', fontsize=9, fontweight='bold', color='#1976d2')
    ax.text(3.7, 5.6, 'STEP 3', fontsize=9, fontweight='bold', color='#1976d2')
    ax.text(7.2, 5.6, 'STEP 4', fontsize=9, fontweight='bold', color='#1976d2')
    ax.text(3.7, 3.1, 'STEP 5', fontsize=9, fontweight='bold', color='#1976d2')
    
    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=module_color, edgecolor=module_edge, label='Agent Modules', linewidth=2),
        mpatches.Patch(facecolor=external_color, edgecolor=external_edge, label='External Services', linewidth=2),
        mpatches.FancyArrow(0, 0, 1, 0, width=0.3, color='#1976d2', label='Data Flow'),
        mpatches.FancyArrow(0, 0, 1, 0, width=0.3, color='#f57c00', linestyle='dotted', label='API Calls')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9, frameon=True, 
             fancybox=True, shadow=True)
    
    # Notes
    notes_text = "5-Step Clinical Triage Workflow:\n" \
                 "1. Normalize structured/text input\n" \
                 "2. Apply deterministic urgency rules (safety baseline)\n" \
                 "3. Retrieve life-threatening diagnoses from knowledge base\n" \
                 "4. LLM provides clinical justification (single API call)\n" \
                 "5. Format nurse-friendly output with KTAS level"
    ax.text(0.5, 0.8, notes_text, fontsize=8, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='#fafafa', edgecolor='#ccc', pad=0.5))
    
    plt.tight_layout()
    
    # Save to static folder
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                               'static', 'architecture.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Architecture diagram saved to: {output_path}")
    plt.close()

if __name__ == '__main__':
    create_architecture_diagram()
