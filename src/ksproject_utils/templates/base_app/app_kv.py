app_kv = """\
<IntroScreen>:
    orientation: 'vertical'
    padding: dp(24)
    spacing: dp(20)
    
    # Background Canvas
    canvas.before:
        Color:
            rgba: (0.10, 0.11, 0.13, 1) # Dark Slate Gray
        Rectangle:
            pos: self.pos
            size: self.size

    # Header / Welcome Section
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.3
        spacing: dp(8)
        
        Label:
            text: "Welcome to Kivy"
            font_size: '28sp'
            bold: True
            color: (1, 1, 1, 1)
            halign: 'center'
            valign: 'middle'
            
        Label:
            id: subtitle_label
            text: "Your journey into cross-platform UI begins here."
            font_size: '14sp'
            color: (0.7, 0.7, 0.7, 1)
            halign: 'center'
            text_size: self.width, None

    # Feature Card (Visual Centerpiece)
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.4
        padding: dp(16)
        spacing: dp(12)
        canvas.before:
            Color:
                rgba: (0.16, 0.18, 0.21, 1) # Lighter card background
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]

        Label:
            text: "Why Kivy?"
            font_size: '18sp'
            bold: True
            color: (0.29, 0.69, 0.31, 1) # Fresh Green Accent
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'left'
            text_size: self.width, None

        Label:
            text: "• Fast & GPU Accelerated\\n• Same code for Android, iOS, Windows, & Mac\\n• Declarative UI with KVLang\\n• Open Source & Flexible"
            font_size: '14sp'
            color: (0.85, 0.85, 0.85, 1)
            line_height: 1.3
            valign: 'top'
            text_size: self.width, self.height

    # Action Section (Button)
    BoxLayout:
        size_hint_y: 0.3
        gravity: 'center'
        padding: [0, dp(40), 0, 0]
        
        Button:
            id: action_btn
            text: "Get Started"
            font_size: '16sp'
            bold: True
            size_hint: (1, None)
            height: dp(50)
            background_color: (0, 0, 0, 0) # Remove default background to style with canvas
            color: (1, 1, 1, 1)
            on_press: root.on_button_click()
            
            canvas.before:
                Color:
                    rgba: (0.29, 0.69, 0.31, 1) if self.state == 'normal' else (0.22, 0.53, 0.24, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [25] # Perfect pill-shaped button
"""