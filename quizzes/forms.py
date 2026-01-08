from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import Profile, College

# -------------------------------------------------------------------
#  UNIVERSAL INPUT STYLE (Glassmorphism)
# -------------------------------------------------------------------
INPUT_STYLE = (
    "w-full pl-12 pr-10 py-3 rounded-xl border border-white/20 "
    "bg-white/10 text-white placeholder-gray-300 "
    "focus:ring-2 focus:ring-purple-500 focus:border-purple-500 "
    "transition duration-200 backdrop-blur-xl"
)

# -------------------------------------------------------------------
#  LOGIN FORM (Clean & Correct)
# -------------------------------------------------------------------
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Email Address',
                'id': 'login_username',
                'autocomplete': 'username'
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Password',
                'id': 'login_password',
                'autocomplete': 'current-password'
            }
        )
    )

    error_messages = {
        'invalid_login': "Invalid email or password. Please try again.",
        'inactive': "This account is inactive.",
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            
            if self.user_cache is None:
                # Check for inactive user with correct credentials
                try:
                    user = User.objects.get(username=username)
                    if user.check_password(password) and not user.is_active:
                        raise forms.ValidationError("Please verify your email first your email is not verified")
                except User.DoesNotExist:
                    pass
                
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

# -------------------------------------------------------------------
#  REGISTRATION FORM
# -------------------------------------------------------------------
class UserRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Full Name',
                'id': 'reg_full_name'
            }
        )
    )
    
    college = forms.ModelChoiceField(
        queryset=College.objects.all(),
        empty_label="Select College",
        widget=forms.Select(
            attrs={
                'class': INPUT_STYLE + " text-black", # text-black for better visibility in dropdown options
                'id': 'reg_college'
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Password',
                'id': 'reg_password'
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Confirm Password',
                'id': 'reg_confirm_password'
            }
        )
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'college', 'password']

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Email Address',
                'id': 'reg_email'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exist please try with another email")
        return email

    # Password match validation
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Set username to email
        
        # Split full name
        full_name = self.cleaned_data['full_name'].strip()
        if " " in full_name:
            first, last = full_name.split(" ", 1)
            user.first_name = first
            user.last_name = last
        else:
            user.first_name = full_name
            user.last_name = ""

        if commit:
            user.save()
            # Handle Profile and College
            college = self.cleaned_data['college']
            if hasattr(user, 'profile'):
                user.profile.college = college
                user.profile.save()
            else:
                Profile.objects.create(user=user, college=college)
                
        return user

# -------------------------------------------------------------------
#  PASSWORD RESET FORM (Email Validation)
# -------------------------------------------------------------------
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm

class EmailValidationPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': INPUT_STYLE,
                'placeholder': 'Enter your email',
                'id': 'reset_email',
                'autocomplete': 'email'
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Wrong email! This email is not registered.")
        return email

# -------------------------------------------------------------------
#  SET NEW PASSWORD FORM
# -------------------------------------------------------------------
class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_STYLE})


# -------------------------------------------------------------------
#  PROFILE FORMS
# -------------------------------------------------------------------
class UserUpdateForm(forms.ModelForm):
    """
    Form to display User model fields (read-only).
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': INPUT_STYLE, 'readonly': 'readonly'})
    )
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'readonly': 'readonly'})
    )

    class Meta:
        model = User
        fields = ['email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            first_name = self.instance.first_name
            last_name = self.instance.last_name
            full_name = f"{first_name} {last_name}".strip()
            
            self.fields['full_name'].initial = full_name
            
            # If name is present, make it read-only. If empty, allow editing.
            if full_name:
                self.fields['full_name'].widget.attrs['readonly'] = 'readonly'
            else:
                self.fields['full_name'].widget.attrs.pop('readonly', None)

    def save(self, commit=True):
        user = super().save(commit=False)
        # Only update name if it was empty (editable)
        if 'readonly' not in self.fields['full_name'].widget.attrs:
            full_name = self.cleaned_data.get('full_name', '').strip()
            if full_name:
                if " " in full_name:
                    first, last = full_name.split(" ", 1)
                    user.first_name = first
                    user.last_name = last
                else:
                    user.first_name = full_name
                    user.last_name = ""
            
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Form to update Profile model fields (editable).
    """
    college = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'readonly': 'readonly'})
    )
    gender = forms.ChoiceField(
        choices=Profile.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': INPUT_STYLE + " [&>option]:text-black"}) # Keep options readable
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': INPUT_STYLE, 'type': 'date'})
    )
    profile_pic = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': INPUT_STYLE})
    )

    class Meta:
        model = Profile
        fields = ['gender', 'date_of_birth', 'profile_pic']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.college:
            self.fields['college'].initial = self.instance.college.name


# -------------------------------------------------------------------
#  QUESTION IMPORT FORM
# -------------------------------------------------------------------
class QuestionImportForm(forms.Form):
    file = forms.FileField(
        label='Upload Excel/CSV File',
        help_text='Supported formats: .xlsx, .xls, .csv',
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls, .csv'})
    )

