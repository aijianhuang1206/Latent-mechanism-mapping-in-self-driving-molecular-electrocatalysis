import ElectroLab as elab

# Set parameters:
fileName = 'CV'
folder = 'C:/User/electrolab/data'
model = 'chi760e'

# Potentiostat setup:
elab.Setup(fileName, folder, model)

# Run experiment:
cv = elab.CV(Eini=-0.5, Ev1=0.5, Ev2=-0.5, Efin=-0.5, sr=0.1, fileName=fileName)
cv.bipot(E=0.5) # Bipotentiostat option available
cv.run()

# Load CV data file:
data = elab.LoadCV(fileName, folder, model)

# Plot CV:
elab.plot(data.E, data.i, xlab='$E$ / V', ylab='$i$ / A')
elab.savefig(fileName)

